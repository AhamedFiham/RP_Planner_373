export const PRIMARY_NUTRIENTS = [
  ['energy_kcal','Energy','kcal'],['carbohydrates_g','Carbohydrates','g'],
  ['proteins_g','Protein','g'],['fat_g','Fat','g'],['fiber_g','Fiber','g'],
];
export const FULL_NUTRIENTS = [
  ['energy_kj','Energy','kJ'],['water_g','Water','g'],['sfa_g','SFA','g'],['mufa_g','MUFA','g'],['pufa_g','PUFA','g'],
  ['vitamin_a_ug','Vitamin A','µg'],['vitamin_b1_mg','Vitamin B1','mg'],['vitamin_b2_mg','Vitamin B2','mg'],
  ['vitamin_b3_mg','Vitamin B3','mg'],['vitamin_b6_mg','Vitamin B6','mg'],['vitamin_b12_mg','Vitamin B12','mg'],
  ['folate_ug','Folate','µg'],['vitamin_c_mg','Vitamin C','mg'],['vitamin_d_ug','Vitamin D','µg'],
  ['vitamin_e_mg','Vitamin E','mg'],['vitamin_k_ug','Vitamin K','µg'],['calcium_mg','Calcium','mg'],
  ['magnesium_mg','Magnesium','mg'],['phosphorus_mg','Phosphorus','mg'],['sodium_mg','Sodium','mg'],
  ['potassium_mg','Potassium','mg'],['iron_mg','Iron','mg'],['zinc_mg','Zinc','mg'],
  ['selenium_ug','Selenium','µg'],['copper_mg','Copper','mg'],['manganese_mg','Manganese','mg'],
];
export const nutrientValue = (value,unit) => value === null || value === undefined ? 'Not available' : `${new Intl.NumberFormat('en-US',{maximumSignificantDigits:6}).format(value)} ${unit}`;
export const referenceBasis = basis => basis === 'per_100g' ? 'per 100 g' : basis === 'per_serving' ? 'per serving' : 'Not available';
export const mappingLabel = status => status?.startsWith('candidate_') ? 'Candidate Mapping' : status === 'representative_full' ? 'Representative Reference' : status === 'needs_source' ? 'Nutrition Data Unavailable' : 'Verified Reference';
export function validateNutritionRecords(data) {
  for (const food of data.foods) {
    const n=food.nutrition;
    const fail=()=>{throw new Error('The service returned an unexpected nutrition reference. Please try again.');};
    if (!n || !['per_100g','per_serving',null].includes(n.nutrition_basis) || !['matched_full','matched_macro','matched_serving','representative_full','candidate_full','candidate_macro','candidate_serving','needs_source'].includes(n.mapping_status) || !['full_macro_micro','macronutrients_only','none'].includes(n.data_completeness)) fail();
    for (const [key] of [...PRIMARY_NUTRIENTS,...FULL_NUTRIENTS]) {
      if (!(key in n) || n[key] !== null && (!Number.isFinite(n[key]) || n[key]<0)) fail();
    }
    if (n.original_serving_quantity !== null && (!Number.isFinite(n.original_serving_quantity) || n.original_serving_quantity<0)) fail();
  }
  return data;
}

// Patient-facing details include source values only; nulls are omitted, zeros retained.
export function nutritionDetailGroups(nutrition) {
  const macros = [...PRIMARY_NUTRIENTS, ...FULL_NUTRIENTS.filter(([key]) => ['energy_kj','water_g','sfa_g','mufa_g','pufa_g'].includes(key))];
  const vitamins = FULL_NUTRIENTS.filter(([key]) => key.startsWith('vitamin_') || key === 'folate_ug');
  const minerals = FULL_NUTRIENTS.filter(([key]) => !macros.some(([macro]) => macro === key) && !vitamins.some(([vitamin]) => vitamin === key));
  return [['Macronutrients', macros], ['Vitamins', vitamins], ['Minerals', minerals]]
    .map(([title,fields]) => ({title, fields:fields.filter(([key])=>nutrition[key]!==null && nutrition[key]!==undefined)}))
    .filter(group=>group.fields.length>0);
}
