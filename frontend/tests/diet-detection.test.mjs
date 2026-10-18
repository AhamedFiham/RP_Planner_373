import test from 'node:test';
import assert from 'node:assert/strict';
import { boxPosition, foodLabel, validateMealFile, validateDetectionResponse } from '../lib/diet-detection.js';
import { detectMeal } from '../lib/api.js';
const detection = { class_id: 9, food_name: 'Chicken_Curry', confidence: .73, bounding_box: { x1: 10, y1: 5, x2: 80, y2: 40 } };
const response = () => ({ success: true, detection_count: 1, detections: [structuredClone(detection)], image_width: 100, image_height: 50 });
test('valid JPG, JPEG, PNG and WebP files', () => {
  for (const [ext,type] of [['jpg','image/jpeg'],['jpeg','image/jpeg'],['png','image/png'],['webp','image/webp']]) assert.equal(validateMealFile({ name:`meal.${ext}`, type, size:100 }), null);
});
test('empty, missing, unsupported and oversized files rejected', () => {
  for (const file of [null,{name:'meal.png',type:'image/png',size:0},{name:'meal.gif',type:'image/gif',size:100},{name:'meal.png',type:'text/plain',size:100},{name:'meal.png',type:'image/png',size:11*1024*1024}]) assert.ok(validateMealFile(file));
});
test('labels preserve backend names', () => { assert.equal(foodLabel(detection.food_name),'Chicken Curry'); assert.equal(detection.food_name,'Chicken_Curry'); });
test('boxes use backend-relative percentages', () => assert.deepEqual(boxPosition(detection.bounding_box,100,50),{left:'10%',top:'10%',width:'70%',height:'70%'}));
test('actual response shape accepted unchanged', () => {const value=response();assert.equal(validateDetectionResponse(value),value);});
test('empty detections are successful', () => assert.equal(validateDetectionResponse({...response(),detection_count:0,detections:[]}).detection_count,0));
test('invalid confidence, class IDs, counts and boxes rejected', () => {
  for (const change of [r=>r.detections[0].confidence=2,r=>r.detections[0].class_id=46,r=>r.detection_count=2,r=>r.detections[0].bounding_box.x2=0,r=>r.image_width=0,r=>r.detections[0].bounding_box.x2=200]) {const value=response();change(value);assert.throws(()=>validateDetectionResponse(value));}
});
test('API sends original File under image with browser-generated Content-Type',async()=>{
  const original=globalThis.fetch;
  try {
    const file=new File(['image'],'meal.jpg',{type:'image/jpeg'});
    globalThis.fetch=async(url,options)=>{assert.ok(url.endsWith('/api/diet/detect-food'));assert.equal(options.method,'POST');assert.equal(options.body.get('image'),file);assert.equal(options.headers,undefined);return {ok:true,json:async()=>response()};};
    assert.equal((await detectMeal(file)).detection_count,1);
  } finally {globalThis.fetch=original;}
});
for (const status of [400,500]) test(`API ${status} uses a safe error message`, async()=>{
  const original=globalThis.fetch;try {globalThis.fetch=async()=>({ok:false,status});await assert.rejects(detectMeal(new File(['x'],'meal.png')),/image|unavailable/);}finally{globalThis.fetch=original;}
});
test('unavailable backend is handled',async()=>{const original=globalThis.fetch;try{globalThis.fetch=async()=>{throw new TypeError('Failed to fetch');};await assert.rejects(detectMeal(new File(['x'],'meal.png')),/unavailable/);}finally{globalThis.fetch=original;}});
test('cancellation propagates for stale-request handling',async()=>{const original=globalThis.fetch;try{globalThis.fetch=async()=>{throw new DOMException('Aborted','AbortError');};await assert.rejects(detectMeal(new File(['x'],'meal.png')),e=>e.name==='AbortError');}finally{globalThis.fetch=original;}});
