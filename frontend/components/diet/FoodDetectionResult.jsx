import { Utensils, LoaderCircle, CircleAlert, ArrowRight } from 'lucide-react';
import DetectionList from './DetectionList';
import { groupedPortionFoods, portionCategoryCounts, patientAnalysisError } from '@/lib/diet-detection';
import styles from './food-detection.module.css';

export default function FoodDetectionResult({ result, loading, error, hasImage, onRetry, onReset }) {
  const foods=result ? groupedPortionFoods(result.detections,result.portion_summary) : [];
  const counts=result ? portionCategoryCounts(result.detections,result.portion_summary) : {};
  return <section className={styles.card} aria-labelledby="results-heading" aria-busy={loading}>
    <div className={styles.cardHeading}><span className={styles.icon}><Utensils size={20}/></span><div><h3 id="results-heading">Meal Summary</h3><p>A closer look at what’s on your plate.</p></div></div>
    <div aria-live="polite">
      {error ? <div className={`${styles.state} ${styles.error}`} role="alert"><CircleAlert size={32}/><h4>We couldn’t analyze this image.</h4><p>{patientAnalysisError(error)}</p>{hasImage && <button className="button" type="button" onClick={onRetry}>Try Again</button>}</div>
      : loading ? <div className={styles.state} role="status"><LoaderCircle size={32} className={styles.spin}/><h4>Analyzing your meal…</h4><p>Your meal summary will be ready shortly.</p></div>
      : result ? foods.length ? <><div className={styles.patientSummary}><strong>{foods.length} {foods.length===1 ? 'food' : 'foods'} identified</strong><div>{['Small','Medium','Large'].map(label=><span key={label}>{label} portions <b>{counts[label]}</b></span>)}</div></div><DetectionList detections={result.detections} summaries={result.portion_summary}/><button type="button" className={styles.another} onClick={onReset}>Analyze Another Meal <ArrowRight size={16}/></button></>
      : <div className={styles.state}><Utensils size={34}/><h4>No foods identified</h4><p>Try a clearer photo with good lighting and visible food items.</p><button type="button" className="button secondary" onClick={onReset}>Choose Another Image</button></div>
      : <div className={styles.state}><span className={styles.emptyIcon}><Utensils size={34}/></span><h4>{hasImage ? 'Ready when you are' : 'Your meal at a glance'}</h4><p>{hasImage ? 'Select Analyze Meal to explore your food and portions.' : 'Choose a meal photo to see its foods, portions and nutrition information.'}</p></div>}
    </div>
  </section>;
}
