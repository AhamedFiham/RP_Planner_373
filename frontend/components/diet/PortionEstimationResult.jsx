import { visualPortionLabel } from '@/lib/diet-detection';
import styles from './food-detection.module.css';

export default function PortionEstimationResult({ portion }) {
  return <div className={styles.patientPortion}><span>Portion</span><strong>{visualPortionLabel(portion.portion_category)}</strong></div>;
}
