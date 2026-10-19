import { nutrientValue } from '@/lib/nutrition-reference';
import { CONSUMED_FIELDS, servingWeightLabel } from '@/lib/consumed-nutrition';
import styles from './food-detection.module.css';

export default function ConsumedNutritionResult({servingWeight: weight, consumed}) {
  return <section className={styles.patientIntake} aria-label="Estimated Intake">
    <h5>Estimated Intake</h5>
    {consumed ? <>
      {weight.estimated_serving_weight_g!==null && <p>Estimated serving: <strong>{servingWeightLabel(weight.estimated_serving_weight_g)}</strong></p>}
      <dl className={styles.patientNutrients}>{CONSUMED_FIELDS.filter(([key])=>consumed[key]!==null && consumed[key]!==undefined).map(([key,label,unit])=><div key={key}><dt>{key==='energy_kcal' ? 'Calories' : label}</dt><dd>{nutrientValue(consumed[key],unit)}</dd></div>)}</dl>
    </> : <p>Serving-based nutrition is not available yet.</p>}
  </section>;
}
