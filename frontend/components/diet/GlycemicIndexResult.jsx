import { giExplanation } from '@/lib/gi-reference';
import styles from './food-detection.module.css';

export default function GlycemicIndexResult({ gi }) {
  const hasValue = gi && typeof gi.gi_value === 'number' && Number.isFinite(gi.gi_value) && gi.gi_category;

  if (!hasValue) {
    return (
      <section className={styles.giPanel} aria-label="Glycemic Index">
        <div className={styles.giHeading}>
          <h5>Glycemic Index</h5>
        </div>
        <p className={styles.giEmpty}>Not available yet</p>
      </section>
    );
  }

  const category = gi.gi_category;
  const explanation = giExplanation(category);
  const badgeClass =
    category === 'Low'
      ? styles.giBadgeLow
      : category === 'Medium'
      ? styles.giBadgeMedium
      : styles.giBadgeHigh;

  return (
    <section className={styles.giPanel} aria-label="Glycemic Index">
      <div className={styles.giHeading}>
        <h5>Glycemic Index</h5>
        <span className={`${styles.giBadge} ${badgeClass}`}>
          GI {Math.round(gi.gi_value)} · {category}
        </span>
      </div>
      {explanation && <p className={styles.giExplanation}>{explanation}</p>}
    </section>
  );
}
