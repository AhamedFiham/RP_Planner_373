'use client';

import { useId } from 'react';
import styles from './analysis.module.css';

export default function HealingChart({ progress }) {
  const chartId = useId();
  const visitCount = progress?.summary?.visit_count ?? 0;

  return (
    <section className={styles.panel} aria-labelledby={`${chartId}-heading`}>
      <div className={styles.panelHeader}>
        <div>
          <p className={styles.eyebrow}>Wound progress</p>
          <h2 id={`${chartId}-heading`} className={styles.heading}>Healing progress</h2>
          <p className={styles.subtitle}>Segmentation masks across wound visits.</p>
        </div>
        <span className={styles.countBadge}>{visitCount} {visitCount === 1 ? 'visit' : 'visits'}</span>
      </div>
      <div className={styles.emptyState}>
        <h3>Graph pending</h3>
        <p>The graph will remain empty until the method for comparing segmentation masks is defined.</p>
      </div>
    </section>
  );
}
