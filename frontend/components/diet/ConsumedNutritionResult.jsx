import { nutrientValue } from '@/lib/nutrition-reference';
import { CONSUMED_FIELDS, servingWeightLabel } from '@/lib/consumed-nutrition';
import styles from './food-detection.module.css';

export default function ConsumedNutritionResult({servingWeight: weight, consumed}) {
  if (!consumed) return null;
  return <section className={styles.patientIntake} aria-label="Estimated Intake">
    <h5>Estimated Intake</h5>
    {weight?.estimated_serving_weight_g!==null && weight?.estimated_serving_weight_g!==undefined && <p>Estimated serving: <strong>{servingWeightLabel(weight.estimated_serving_weight_g)}</strong></p>}
    <dl className={styles.patientNutrients}>{CONSUMED_FIELDS.filter(([key])=>consumed[key]!==null && consumed[key]!==undefined).map(([key,label,unit])=><div key={key}><dt>{key==='energy_kcal' ? 'Calories' : label}</dt><dd>{nutrientValue(consumed[key],unit)}</dd></div>)}</dl>
  </section>;
}
