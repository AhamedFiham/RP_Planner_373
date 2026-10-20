import styles from './food-detection.module.css';
export default function GlycemicLoadResult({value}) {
  const available=value?.calculation_status==='calculated' && Number.isFinite(value.glycemic_load);
  return <section className={styles.giPanel} aria-label="Glycemic Load"><div className={styles.giHeading}><h5>Glycemic Load</h5>{available && <span className={styles.giBadge}> {value.glycemic_load.toFixed(1)} · {value.gl_category}</span>}</div><p className={styles.giExplanation}>{available ? (value.gl_category==='Low'?'Lower glycemic impact for this portion.':value.gl_category==='Medium'?'Moderate glycemic impact for this portion.':'Higher glycemic impact for this portion.') : 'Not available yet'}</p></section>;
}
