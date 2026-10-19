import { boxPosition, foodLabel } from '@/lib/diet-detection';
import styles from './food-detection.module.css';

export default function DetectionImage({ src, result }) {
  return <div className={styles.imageFrame} style={result ? { aspectRatio: `${result.image_width} / ${result.image_height}` } : undefined}>
    {/* Blob previews require a native img and retain the source image dimensions. */}
    <img src={src} alt="Your meal photo with identified foods" className={styles.mealImage} style={result ? { height: '100%' } : undefined}/>
    {result?.detections.map((d, index) => <div key={`${d.class_id}-${index}`} className={styles.box} style={boxPosition(d.bounding_box, result.image_width, result.image_height)} aria-hidden="true"><span className={styles.boxLabel}>{foodLabel(d.food_name)}</span></div>)}
  </div>;
}
