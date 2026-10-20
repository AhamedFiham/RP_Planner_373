import styles from './food-detection.module.css';
export default function AvailableCarbohydrateResult({value}) {
  if (!value) return null;
  const hasConsumed = value.calculation_status === 'calculated' && value.validated && Number.isFinite(value.consumed_available_carbohydrate_g);
  const hasReference = Number.isFinite(value.reference_value_g);
  return <section className={styles.patientIntake} aria-label="Available Carbohydrate"><h5>Available Carbohydrate</h5>{hasConsumed ? <p><strong>{value.consumed_available_carbohydrate_g.toFixed(1)} g</strong><br/><small>Carbohydrate expected to contribute to blood glucose response.</small></p> : hasReference ? <p>Reference: {value.reference_value_g} g {value.reference_basis === 'per_100g' ? 'per 100 g' : 'per serving'}</p> : <p>Not available yet</p>}</section>;
}
