import { validatePortionResponse } from './diet-detection.js';
import { validateNutritionRecords } from './nutrition-reference.js';

export const CONSUMED_FIELDS = [['energy_kcal','Energy','kcal'],['carbohydrates_g','Carbohydrates','g'],['proteins_g','Protein','g'],['fat_g','Fat','g'],['fiber_g','Fiber','g']];
export const servingWeightLabel = weight => weight === null ? 'Not available yet' : `${new Intl.NumberFormat('en-US',{maximumSignificantDigits:6}).format(weight)} g`;
export function validateConsumedResponse(data) {
  const fail=()=>{throw new Error('The service returned an unexpected serving-weight estimate. Please try again.');};
  if(!data || !Array.isArray(data.detections) || !Array.isArray(data.foods))fail();
  const normalized=validatePortionResponse({...data,foods:data.detections});
  validateNutritionRecords({foods:normalized.detections});
  const groups=new Map();
  for(const food of data.foods){
    const w=food.serving_weight,c=food.consumed_nutrition,key=`${food.class_id}:${food.food_name}`;
    if(groups.has(key) || !w || !['portion_category','count_based','reference_serving','unsupported'].includes(w.serving_method) || typeof w.validated!=='boolean')fail();
    const mass=w.estimated_serving_weight_g;
    if(mass!==null && (!Number.isFinite(mass)||mass<=0||!w.validated||w.serving_weight_status!=='available'))fail();
    if(mass===null && (c!==null || w.serving_weight_status==='available'))fail();
    if(c!==null){
      if(mass===null||!c||food.consumed_nutrition_status!=='estimated')fail();
      for(const key of ['energy_kcal','energy_kj','carbohydrates_g','proteins_g','fat_g','fiber_g'])if(!(key in c)||c[key]!==null&&(!Number.isFinite(c[key])||c[key]<0))fail();
    }
    groups.set(key,food);
  }
  const seen=new Set();
  const detections=normalized.detections.map(d=>{
    const key=`${d.class_id}:${d.food_name}`,group=groups.get(key);if(!group)fail();seen.add(key);
    return {...d,serving_weight:group.serving_weight,consumed_nutrition:group.consumed_nutrition,consumed_nutrition_status:group.consumed_nutrition_status};
  });
  if(seen.size!==groups.size)fail();
  // Attach food-level estimates for cards only; no box or confidence is changed.
  return {...normalized,foods:data.foods,detections};
}
