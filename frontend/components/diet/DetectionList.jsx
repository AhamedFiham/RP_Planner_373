import { CircleCheck } from 'lucide-react';
import { foodLabel } from '@/lib/diet-detection';
import styles from './food-detection.module.css';

export default function DetectionList({ detections }) {
  return <ol className={styles.detectionList}>{[...detections].sort((a,b) => b.confidence - a.confidence).map((d,index) => {
    const status = d.confidence >= .75 ? 'High' : d.confidence >= .5 ? 'Medium' : 'Low';
    return <li key={`${d.class_id}-${index}`}><div className={styles.resultTop}><span className={styles.foodIcon}><CircleCheck size={18}/></span><div><h4>{foodLabel(d.food_name)}</h4><span className={styles.classId}>Class ID {d.class_id}</span></div><strong>{(d.confidence * 100).toFixed(1)}<small>%</small></strong></div><div className={styles.confidenceTrack} aria-hidden="true"><span style={{ width: `${d.confidence * 100}%` }}/></div><div className={styles.confidenceCaption}><span>{status} confidence</span><span>Detection {index+1}</span></div></li>;
  })}</ol>;
}
