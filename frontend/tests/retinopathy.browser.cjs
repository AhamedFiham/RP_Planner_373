// Mock browser verification only; requires Playwright and locally installed Chrome.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const context=await browser.newContext();
await context.addInitScript(()=>{if(location.protocol !== 'http:') return;localStorage.setItem('dcare_token','browser-test-only');localStorage.setItem('dcare_user',JSON.stringify({email:'test@example.com',name:'Test'}));localStorage.setItem('dcare_dashboard','/dashboard/retinopathy');window.__created=[];window.__revoked=[];const create=URL.createObjectURL;const revoke=URL.revokeObjectURL;URL.createObjectURL=(b)=>{const u=create(b);window.__created.push(u);return u;};URL.revokeObjectURL=(u)=>{window.__revoked.push(u);revoke(u);};});
const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
const keys=['no_dr','mild_npdr','moderate_npdr','severe_npdr','proliferative_dr'];const id='a'.repeat(24),aid='b'.repeat(24);let scenario='missing',deletes=0,artifacts=0,requests=0;
// Use a browser-decoded canvas PNG as upload/artifact fixture, never model evidence.
await page.goto('about:blank');
const bytes=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=64;return c.toDataURL().split(',')[1];});const image=Buffer.from(bytes,'base64');
await page.route('http://127.0.0.1:8000/api/**',async route=>{
const req=route.request();assert.equal(req.headers().authorization,'Bearer browser-test-only');const path=new URL(req.url()).pathname;
if(path.endsWith('/health')) return route.fulfill({json:{ready:false,quality:{state:'missing_artifact'}}});
if(path.endsWith('/history')) return route.fulfill({json:{items:scenario==='history'?[{id,created_at:'2026-10-15T00:00:00Z',assessment_status:'failed',image_quality:null}]:[],total:scenario==='history'?11:0,page:1,limit:10}});
if(path.includes('/artifacts/')){artifacts++;return route.fulfill({contentType:'image/png',body:image});}
if(path.endsWith('/assessments/'+id)){if(req.method()==='DELETE'){deletes++;return route.fulfill({status:204});}return route.fulfill({json:{id,assessment_status:'failed',image_quality:null,artifacts:[]}});}
if(path.endsWith('/analyze')){requests++;if(scenario==='missing')return route.fulfill({status:503,json:{status:'model_unavailable'}});const rejected=scenario==='reject';return route.fulfill({json:{status:rejected?'quality_rejected':'completed',assessment_id:id,image_quality:{label:rejected?'Reject':scenario==='usable'?'Usable':'Good',gate:rejected?'reupload':'proceed',confidence:.9,probabilities:{Good:.9,Usable:.05,Reject:.05},model_version:'mock-only'},prediction:rejected?null:{class_id:2,class_name:'Moderate NPDR',confidence:.6,is_calibrated:scenario!=='raw',probabilities:Object.fromEntries(keys.map((k,i)=>[k,i===2?.6:.1])),model_version:'mock-only'},reliability:{status:'uncertain_prediction',requires_review:true,reason:'Professional review required.'},guidance:{message:'Professional review required.'},gradcam:{available:!rejected,original:`/api/retinopathy/assessments/${id}/artifacts/${aid}`,artifacts:rejected?{}:Object.fromEntries(keys.map((k,i)=>[k,{heatmap:`/api/retinopathy/assessments/${id}/artifacts/${String(i+1).repeat(24)}`,overlay:`/api/retinopathy/assessments/${id}/artifacts/${(i+6).toString(16).repeat(24)}`}]))}}});}
return route.fulfill({json:{}});
});
await page.goto((process.env.RETINO_UI_URL || 'http://127.0.0.1:3001') + '/retinopathy');
await page.getByText('required models are not ready',{exact:false}).waitFor();
await page.locator('#retinal-file').setInputFiles({name:'test.png',mimeType:'image/png',buffer:image});
await page.getByRole('button',{name:'Analyze Retinal Image',exact:true}).click();await page.getByText('Required models are not ready.',{exact:false}).last().waitFor();assert.equal(await page.locator('.retino-results').count(),0);
scenario='reject';await page.getByRole('button',{name:'Analyze Retinal Image',exact:true}).click();await page.getByText('Severity analysis stopped.').waitFor();assert.equal(await page.locator('.retino-results').count(),0);
scenario='raw';await page.getByRole('button',{name:'Analyze Retinal Image',exact:true}).click();await page.getByText('Uncalibrated Probabilities',{exact:true}).waitFor();await page.waitForFunction(()=>document.querySelectorAll('.retino-comparison-panel img').length===5);assert.ok(artifacts>=11);assert.equal(await page.locator('.retino-comparison-panel').count(),5);
scenario='usable';await page.getByRole('button',{name:'Analyze Retinal Image',exact:true}).click();await page.getByText('Calibrated Probabilities',{exact:true}).waitFor();await page.getByText('Usable with caution — accepted by backend').waitFor();
scenario='history';await page.getByRole('button',{name:'Refresh history',exact:true}).click();await page.getByRole('button',{name:'View details',exact:true}).click();await page.getByText('No saved severity prediction.',{exact:false}).waitFor();await page.getByRole('button',{name:'Delete',exact:true}).click();await page.getByRole('button',{name:'Confirm deletion',exact:true}).click();await page.waitForTimeout(200);assert.equal(deletes,1);
await page.getByRole('button',{name:'Remove selected image',exact:true}).click();await page.waitForTimeout(100);const cleanup=await page.evaluate(()=>({created:__created.length,revoked:__revoked.length}));assert.equal(cleanup.created,cleanup.revoked);assert.equal(errors.length,0,errors.join('\n'));
await page.getByRole('button',{name:'Sign out',exact:true}).first().click();await page.waitForURL('**/login');assert.equal(await page.locator('.retino-page').count(),0);
console.log(JSON.stringify({browser:'Chrome',checks:'page, preview, unavailable, reject, raw probabilities, five authenticated images, history, details, confirmed delete, object URL cleanup',requests,artifacts,cleanup,pageErrors:errors}));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
