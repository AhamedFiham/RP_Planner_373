import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRetinopathyApi, artifactPath, errorMessage } from '../lib/retinopathy/api.js';
import { normalizeAnalysis, normalizeRecord } from '../lib/retinopathy/contract.js';
import { CLASS_KEYS, percent, validateRetinalFile } from '../lib/retinopathy/constants.js';
const distribution = Object.fromEntries(CLASS_KEYS.map((k,i)=>[k,i===2?.6:.1]));
function response(label='Good',gate='proceed') { return { status:gate==='proceed'?'completed':'quality_rejected', assessment_id:'a'.repeat(24), image_quality:{ label, gate },
 prediction:gate==='proceed'?{class_id:2,class_name:'Moderate NPDR',confidence:.6,is_calibrated:true,probabilities:distribution,model_version:'test'}:null,
 gradcam:{available:gate==='proceed',artifacts:{}},reliability:{status:'uncertain_prediction',requires_review:true},guidance:{message:'Review required'} }; }
for(const label of ['Good','Usable']) test(`${label} accepted only by backend gate`,()=>assert.equal(normalizeAnalysis(response(label)).result.confidence,.6));
for(const label of ['Reject','Usable']) test(`${label} rejected has no prediction`,()=>assert.equal(normalizeAnalysis(response(label,'reupload')).result,null));
test('five classes retain numeric fractions and formatting',()=>{const r=normalizeAnalysis(response()).result;assert.deepEqual(r.probabilities,[.1,.1,.6,.1,.1]);assert.equal(percent(r.confidence),'60.0%');assert.equal(r.reliability.requires_review,true);});
test('reject cannot contain severity',()=>{const r=response('Reject','reupload');r.prediction=response().prediction;assert.throws(()=>normalizeAnalysis(r));});
test('reject invalid probabilities or class mapping',()=>{const r=response();r.prediction={...r.prediction,class_name:'No DR'};assert.throws(()=>normalizeAnalysis(r));r.prediction={...response().prediction,probabilities:{...distribution,no_dr:9}};assert.throws(()=>normalizeAnalysis(r));});
test('uncalibrated status retained',()=>{const r=response();r.prediction.is_calibrated=false;assert.equal(normalizeAnalysis(r).result.calibrated,false);});
test('partial response remains partial',()=>{const r=response();r.status='partial';r.gradcam.available=false;assert.equal(normalizeAnalysis(r).result.gradcam.available,false);});
test('historical failures have no generated result',()=>assert.equal(normalizeRecord({assessment_status:'failed'}),null));
test('file validation and maximum size',()=>{assert.equal(validateRetinalFile({name:'x.jpg',type:'image/jpeg',size:10}), '');for(const f of [{name:'x.txt',type:'text/plain',size:1},{name:'x.png',type:'image/png',size:0},{name:'x.png',type:'image/png',size:11*1024*1024}])assert.ok(validateRetinalFile(f));});
test('artifact references cannot exfiltrate bearer tokens',()=>{for(const url of ['https://evil.test/x','//evil.test/x','/api/auth/me','/api/retinopathy/artifacts/../x'])assert.throws(()=>artifactPath(url));assert.equal(artifactPath(`/api/retinopathy/assessments/${'a'.repeat(24)}/artifacts/${'b'.repeat(24)}`).startsWith('/api'),true);});
test('safe error messages',()=>{assert.match(errorMessage(401),/session/);assert.match(errorMessage(503,'model_unavailable'),/models/);assert.match(errorMessage(503),/unavailable/);});
test('authenticated multipart without manual content type; history pagination and deletion',async()=>{
 const previous=global.fetch; const requests=[];
 global.fetch=async(url,options)=>{requests.push({url,options});return new Response(options.method==='DELETE'?null:'{}',{status:options.method==='DELETE'?204:200,headers:{'Content-Type':'application/json'}});};
 try {const api=createRetinopathyApi('test-token');await api.analyze(new Blob(['image'],{type:'image/png'}));await api.history(2);await api.remove('a'.repeat(24));assert.equal(requests[0].options.headers.Authorization,'Bearer test-token');assert.equal(requests[0].options.headers['Content-Type'],undefined);assert.ok(requests[0].options.body.get('image'));assert.match(requests[1].url,/page=2&limit=10/);assert.equal(requests[2].options.method,'DELETE');} finally {global.fetch=previous;}
});
test('401 invokes existing logout callback and hides server details',async()=>{
 const previous=global.fetch;let loggedOut=false;global.fetch=async()=>new Response(JSON.stringify({detail:'/private/server/secret'}),{status:401});
 try {await assert.rejects(()=>createRetinopathyApi('test',()=>loggedOut=true).health(),/session/);assert.equal(loggedOut,true);}finally{global.fetch=previous;}
});
test('aborted requests propagate without success',async()=>{
 const previous=global.fetch;global.fetch=async()=>{throw new DOMException('Aborted','AbortError');};
 try{await assert.rejects(()=>createRetinopathyApi('test').health(),{name:'AbortError'});}finally{global.fetch=previous;}
});
