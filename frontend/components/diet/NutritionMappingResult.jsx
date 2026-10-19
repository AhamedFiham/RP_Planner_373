import { PRIMARY_NUTRIENTS, nutrientValue, referenceBasis, nutritionDetailGroups } from '@/lib/nutrition-reference';
import styles from './food-detection.module.css';

export default function NutritionMappingResult({ nutrition: n }) {
  const groups=nutritionDetailGroups(n);
  const available=n.mapping_status!=='needs_source' && groups.length>0;
  if (!available) return <section className={styles.nutritionPanel} aria-label="Nutrition Information"><h5 className={styles.consumedHeading}>Nutrition Information</h5><p className={styles.nutritionEmpty}>Not available yet</p></section>;
  const primary=PRIMARY_NUTRIENTS.filter(([key])=>n[key]!==null && n[key]!==undefined);
  return <section className={styles.nutritionPanel} aria-label="Reference Nutrition">
    <div className={styles.nutritionHeading}><h5>Reference Nutrition</h5><span className={styles.patientBasis}>{referenceBasis(n.nutrition_basis)}</span></div>
    {n.nutrition_basis==='per_serving' && n.original_serving_quantity!==null && <p className={styles.basis}>Serving reference: {n.original_serving_quantity} {n.original_serving_unit || ''}</p>}
    <dl className={styles.patientNutrients}>{primary.map(([key,label,unit])=><div key={key}><dt>{label}</dt><dd>{nutrientValue(n[key],unit)}</dd></div>)}</dl>
    <details className={styles.patientDetails}><summary>View Nutrition Details</summary>
      {groups.map(group=><section key={group.title}><h6>{group.title}</h6><dl>{group.fields.map(([key,label,unit])=><div key={key}><dt>{label}</dt><dd>{nutrientValue(n[key],unit)}</dd></div>)}</dl></section>)}
      {n.source_name && <p className={styles.nutritionSource}><strong>Source:</strong> {n.source_name}</p>}
    </details>
  </section>;
}
