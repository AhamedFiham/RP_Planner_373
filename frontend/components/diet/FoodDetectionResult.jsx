import { ScanLine, LoaderCircle, CircleAlert, Utensils, ArrowRight } from 'lucide-react';
import DetectionList from './DetectionList';
import styles from './food-detection.module.css';

export default function FoodDetectionResult({ result, loading, error, hasImage, onRetry, onReset }) {
  return <section className={styles.card} aria-labelledby="results-heading" aria-busy={loading}>
    <div className={styles.cardHeading}><span className={styles.icon}><ScanLine size={20}/></span><div><h3 id="results-heading">Detection Results</h3><p>Food identities, directly from your image.</p></div><span className={styles.step}>02</span></div>
    <div aria-live="polite" aria-atomic="true">
      {error ? <div className={`${styles.state} ${styles.error}`} role="alert"><CircleAlert size={32}/><h4>We couldn’t analyze this image.</h4><p>{error}</p>{hasImage ? <button className="button" onClick={onRetry}>Try Again</button> : <p>Choose another image to continue.</p>}</div>
      : loading ? <div className={styles.state} role="status"><LoaderCircle size={36} className={styles.spin}/><h4>Analyzing your meal…</h4><p>Identifying supported Sri Lankan food items.</p></div>
      : result ? result.detection_count ? <><div className={styles.summary}><div><span>Foods Identified</span><strong>{result.detection_count}<small> {result.detection_count === 1 ? 'item' : 'items'}</small></strong></div><span className={styles.complete}>Analysis complete</span></div><DetectionList detections={result.detections}/><p className={styles.resultNote}>Confidence describes the model’s prediction, not nutritional suitability. Check the food identities before using them.</p><button type="button" className={styles.another} onClick={onReset}>Analyze Another Meal <ArrowRight size={16}/></button></>
      : <div className={styles.state}><Utensils size={34}/><h4>No supported foods detected</h4><p>Try another image with clear lighting and visible food items.</p><button className="button secondary" onClick={onReset}>Choose Another Image</button></div>
      : <div className={styles.state}><span className={styles.emptyIcon}><ScanLine size={34}/></span><h4>{hasImage ? 'Ready when you are' : 'Your results will appear here'}</h4><p>{hasImage ? 'Select Analyze Meal to identify the foods in your image.' : 'Upload a meal image to begin. Detected foods and their confidence scores will appear here.'}</p><div className={styles.emptySteps}><span>1 Upload</span><span>2 Analyze</span><span>3 Review</span></div></div>}
    </div>
  </section>;
}
