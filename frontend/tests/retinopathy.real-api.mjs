// Use only the disposable runner; no application account or patient data is accessed.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { createRetinopathyApi } from '../lib/retinopathy/api.js';
const base=process.env.NEXT_PUBLIC_API_URL;
if (!process.env.RETINO_DISPOSABLE_TEST || !base) throw new Error('Use the disposable integration runner.');
const password='TestOnly9'+randomUUID(),email=`test-${randomUUID()}@example.com`;
const registration={email,password,confirm_password:password,name:'Disposable Test',username:'testuser',phone:'0712345678',is_diabetic:true};
assert.ok((await fetch(base+'/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(registration)})).ok);
const login=await fetch(base+'/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});assert.ok(login.ok);
const {access_token}=await login.json();assert.ok(access_token);const api=createRetinopathyApi(access_token);
const health=await api.health();assert.equal(health.ready,false);assert.equal(health.quality.state,'missing_artifact');
assert.equal((await api.history()).total,0);
const image=new File([await readFile(process.env.RETINO_FUNDUS_SAMPLE)],'fundus.png',{type:'image/png'});
await assert.rejects(()=>api.analyze(image),e=>e.status===503 && e.code==='model_unavailable');
// Readiness is checked before storing images or creating assessment records.
const history=await api.history();assert.equal(history.total,0);
const unauthenticatedUpload=new FormData();unauthenticatedUpload.append('image',image);
assert.equal((await fetch(base+'/api/retinopathy/analyze',{method:'POST',body:unauthenticatedUpload})).status,401);
await assert.rejects(()=>api.detail('a'.repeat(24)),e=>e.status===404);
const cors=await fetch(base+'/api/retinopathy/history',{method:'OPTIONS',headers:{Origin:'http://127.0.0.1:3000','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization'}});assert.equal(cors.headers.get('access-control-allow-origin'),'http://127.0.0.1:3000');
console.log(JSON.stringify({realApiClient:true,login:true,health:health.status,analysis:'503 model_unavailable',unauthenticatedAnalysis:401,assessmentCreated:false,emptyHistoryVerified:true,missingDetail:404,cors:true}));
