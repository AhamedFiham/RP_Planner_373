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

import { validatePortionResponse, visibleAreaLabel, portionMethodLabel } from '../lib/diet-detection.js';
import { estimateMealPortions } from '../lib/api.js';
const portion = {method:'area_based',relative_area:.094,count:null,portion_category:'Needs Calibration',estimated_grams:null,validated:false};
const portions = () => ({...response(),foods:[{...detection,portion:{...portion}}],portion_summary:[{class_id:9,food_name:'Chicken_Curry',...portion}]});
test('portion labels match the research baseline display',()=>{
 assert.equal(visibleAreaLabel(.094),'9.4%');
 assert.equal(visibleAreaLabel(0),'0.0%');
 assert.equal(visibleAreaLabel(null),'Not applicable');
 assert.equal(portionMethodLabel('area_based'),'Area Based');
});
test('portion normalization preserves detections and metadata',()=>{
 const value=validatePortionResponse(portions());
 assert.equal(value.detections[0].portion.relative_area,.094);
 assert.equal(value.portion_summary[0].estimated_grams,null);
});
test('portion response refuses invalid areas and unsupported gram claims',()=>{
 for(const update of [{relative_area:2},{estimated_grams:100},{validated:true},{count:-1}]) {
  const value=portions();Object.assign(value.foods[0].portion,update);
  assert.throws(()=>validatePortionResponse(value));
 }
});
test('portion API uploads original file once to the new endpoint',async()=>{
 const original=globalThis.fetch;
 try{
  const file=new File(['image'],'meal.png',{type:'image/png'});
  globalThis.fetch=async(url,options)=>{assert.ok(url.endsWith('/api/diet/estimate-portions'));assert.equal(options.body.get('image'),file);return {ok:true,json:async()=>portions()};};
  assert.equal((await estimateMealPortions(file)).detections.length,1);
 }finally{globalThis.fetch=original;}
});

import { groupedPortionFoods, visualPortionLabel, portionCategoryCounts } from '../lib/diet-detection.js';
test('duplicate boxes remain intact while portion cards group by food',()=>{
 const detections=[{...detection,class_id:13,food_name:'Cutlet',confidence:.7},{...detection,class_id:13,food_name:'Cutlet',confidence:.8}];
 const before=JSON.stringify(detections);
 const summary={class_id:13,food_name:'Cutlet',method:'count_based',count:2,portion_category:'Medium',estimated_grams:null,validated:false};
 const grouped=groupedPortionFoods(detections,[summary]);
 assert.equal(grouped.length,1);assert.equal(grouped[0].portion.count,2);assert.equal(grouped[0].portion.portion_category,'Medium');
 assert.equal(grouped[0].confidence,.8);assert.equal(JSON.stringify(detections),before);
});
test('area duplicates use the backend grouped category, not per-box bins',()=>{
 const detections=[{...detection,portion:{...portion,portion_category:'Small'}},{...detection,portion:{...portion,portion_category:'Small'}}];
 const summary={class_id:9,food_name:'Chicken_Curry',...portion,portion_category:'Large'};
 assert.equal(groupedPortionFoods(detections,[summary])[0].portion.portion_category,'Large');
 assert.deepEqual(portionCategoryCounts(detections,[summary]),{Small:0,Medium:0,Large:1,Unknown:0});
});
test('visual labels keep categories and safely handle unsupported cases',()=>{
 for(const label of ['Small','Medium','Large','Unknown'])assert.equal(visualPortionLabel(label),label);
 assert.equal(visualPortionLabel('Needs Calibration'),'Unknown');
 assert.equal(groupedPortionFoods([detection],[])[0].portion.portion_category,'Unknown');
});

import { PRIMARY_NUTRIENTS, FULL_NUTRIENTS, nutrientValue, referenceBasis, mappingLabel, validateNutritionRecords } from '../lib/nutrition-reference.js';
import { mapMealNutrition } from '../lib/api.js';
function nutritionFixture(overrides={}) {
 return {...Object.fromEntries([...PRIMARY_NUTRIENTS,...FULL_NUTRIENTS].map(([key])=>[key,null])),nutrition_basis:'per_100g',mapping_status:'matched_full',data_completeness:'full_macro_micro',original_serving_quantity:null,...overrides};
}
test('missing nutrition stays unavailable while explicit zero displays zero',()=>{
 assert.equal(nutrientValue(null,'g'),'Not available');assert.equal(nutrientValue(0,'g'),'0 g');assert.equal(nutrientValue(123.82,'kcal'),'123.82 kcal');
});
test('reference basis and mapping badges preserve distinctions',()=>{
 assert.equal(referenceBasis('per_100g'),'per 100 g');assert.equal(referenceBasis('per_serving'),'per serving');
 for(const status of ['candidate_full','candidate_macro','candidate_serving'])assert.equal(mappingLabel(status),'Candidate Mapping');
 assert.equal(mappingLabel('representative_full'),'Representative Reference');assert.equal(mappingLabel('needs_source'),'Nutrition Data Unavailable');assert.equal(mappingLabel('matched_serving'),'Verified Reference');
});
test('nutrition validation preserves per-serving numbers without conversion',()=>{
 const value=portions();value.foods[0].nutrition=nutritionFixture({nutrition_basis:'per_serving',original_serving_quantity:10,original_serving_unit:'g',energy_kcal:12,data_completeness:'none',mapping_status:'matched_serving'});
 assert.equal(validateNutritionRecords(value).foods[0].nutrition.energy_kcal,12);
});
test('nutrition nulls accepted and invalid numeric references rejected',()=>{
 const value=portions();value.foods[0].nutrition=nutritionFixture({mapping_status:'needs_source',nutrition_basis:null,data_completeness:'none'});assert.equal(validateNutritionRecords(value),value);
 value.foods[0].nutrition.energy_kcal=NaN;assert.throws(()=>validateNutritionRecords(value));
});
test('one nutrition upload uses image field and preserves grouped nutrition',async()=>{
 const original=globalThis.fetch;const data=portions();data.foods[0].nutrition=nutritionFixture({energy_kcal:123.82});
 try{globalThis.fetch=async(url,options)=>{assert.ok(url.endsWith('/api/diet/map-nutrition'));assert.ok(options.body.get('image') instanceof File);return {ok:true,json:async()=>data};};
 const result=await mapMealNutrition(new File(['x'],'meal.png',{type:'image/png'}));
 assert.equal(result.detections[0].nutrition.energy_kcal,123.82);assert.equal(groupedPortionFoods(result.detections,result.portion_summary)[0].nutrition.energy_kcal,123.82);
 }finally{globalThis.fetch=original;}
});

import { servingWeightLabel, validateConsumedResponse } from '../lib/consumed-nutrition.js';
import { estimateMealConsumedNutrition } from '../lib/api.js';
function consumedFixture(available=false){
 const food={...detection,portion:{...portion},nutrition:nutritionFixture({energy_kcal:120})};
 const serving_weight={serving_method:'portion_category',estimated_serving_weight_g:available?50:null,serving_weight_status:available?'available':'needs_reference',validated:available,source_name:available?'TEST ONLY':null,source_reference:available?'TEST ONLY':null};
 const consumed_nutrition=available?{energy_kcal:60,energy_kj:null,carbohydrates_g:null,proteins_g:null,fat_g:0,fiber_g:null,scaling_factor:.5,calculation_basis:'per_100g_weight_scaling'}:null;
 return {...response(),foods:[{...food,serving_weight,consumed_nutrition,consumed_nutrition_status:available?'estimated':'serving_weight_unavailable'}],detections:[food],portion_summary:[{class_id:9,food_name:'Chicken_Curry',...portion}]};
}
test('serving mass is unavailable rather than fake zero and actual sourced mass formats',()=>{
 assert.equal(servingWeightLabel(null),'Not available yet');assert.equal(servingWeightLabel(50),'50 g');
});
test('new grouped consumed response preserves detection boxes and missing consumed values',()=>{
 const data=consumedFixture();const boxes=JSON.stringify(data.detections[0].bounding_box);const out=validateConsumedResponse(data);
 assert.equal(out.detections[0].consumed_nutrition,null);assert.equal(JSON.stringify(out.detections[0].bounding_box),boxes);assert.equal(out.detections[0].nutrition.energy_kcal,120);
});
test('sourced consumed values keep explicit zero and null separate',()=>{
 const out=validateConsumedResponse(consumedFixture(true));assert.equal(out.detections[0].consumed_nutrition.fat_g,0);assert.equal(out.detections[0].consumed_nutrition.fiber_g,null);
});
test('unavailable mass cannot carry invented consumed values',()=>{
 const data=consumedFixture();data.foods[0].consumed_nutrition={energy_kcal:10};assert.throws(()=>validateConsumedResponse(data));
});
test('one consumed-nutrition upload goes to new endpoint and older helpers remain intact',async()=>{
 const original=globalThis.fetch;try{globalThis.fetch=async(url,options)=>{assert.ok(url.endsWith('/api/diet/estimate-consumed-nutrition'));assert.ok(options.body.get('image') instanceof File);return{ok:true,json:async()=>consumedFixture()};};const result=await estimateMealConsumedNutrition(new File(['x'],'meal.png',{type:'image/png'}));assert.equal(result.detections.length,1);}finally{globalThis.fetch=original;}
});

test('small positive nutrient values are not rounded into fake zeros',()=>{assert.equal(nutrientValue(.0004,'g'),'0.0004 g');});


import { nutritionDetailGroups } from '../lib/nutrition-reference.js';
import { patientAnalysisError } from '../lib/diet-detection.js';
test('patient nutrition accordion groups available values and preserves source zero',()=>{
 const value=nutritionFixture({energy_kcal:120,vitamin_a_ug:0,calcium_mg:10});
 const groups=nutritionDetailGroups(value);
 assert.deepEqual(groups.map(g=>g.title),['Macronutrients','Vitamins','Minerals']);
 assert.ok(groups[1].fields.some(([key])=>key==='vitamin_a_ug'));
 assert.ok(!groups.flatMap(g=>g.fields).some(([key])=>key==='fiber_g'));
 assert.equal(nutritionDetailGroups(nutritionFixture()).length,0);
});
test('patient errors avoid backend/model terminology',()=>{
 for(const message of ['YOLO failed at /private/model.pt','portion inference failure','Food detection service unavailable'])assert.ok(!/YOLO|private|inference|detection|backend/i.test(patientAnalysisError(message)));
 assert.match(patientAnalysisError('Check your connection'),/connection/);
});
