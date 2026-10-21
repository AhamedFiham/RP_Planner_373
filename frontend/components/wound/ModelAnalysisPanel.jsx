'use client';

import { useId } from 'react';
import styles from './analysis.module.css';

const modelStages = [
  {
    number: '01',
    title: 'Wound segmentation',
    description: 'Generate a segmentation mask for a wound image.',
    outputs: ['Wound segmentation mask'],
    placeholder: 'The wound mask will appear here after model integration.',
  },
  {
    number: '02',
    title: 'Tissue segmentation',
    description: 'Identify tissue regions within the wound.',
    outputs: ['Tissue segmentation mask'],
    placeholder: 'The tissue mask will appear here after model integration.',
  },
  {
    number: '03',
    title: 'Healing process analysis',
    description: 'Review segmentation masks across wound visits.',
    outputs: ['Healing assessment method to be defined'],
    placeholder: 'Awaiting the segmentation-mask comparison method before integration.',
  },
];

export default function ModelAnalysisPanel({ visit }) {
  const panelId = useId();

  return (
    <section className={styles.panel} aria-labelledby={`${panelId}-heading`}>
      <div className={styles.panelHeader}>
        <div>
          <p className={styles.eyebrow}>Analysis pipeline</p>
          <h2 id={`${panelId}-heading`} className={styles.heading}>Three models. One wound timeline.</h2>
          <p className={styles.subtitle}>{visit ? 'Analysis workspace for the selected visit.' : 'Select a recorded visit to review its analysis workspace.'}</p>
        </div>
        <span className={styles.pendingBadge}><span aria-hidden="true" />Integration pending</span>
      </div>
      <div className={styles.modelGrid}>
        {modelStages.map(model => (
          <article className={styles.modelCard} key={model.number}>
            <div className={styles.modelTop}><span className={styles.modelNumber}>{model.number}</span><span className={styles.modelStatus}>Not connected</span></div>
            <h3>{model.title}</h3>
            <p className={styles.modelDescription}>{model.description}</p>
            <div className={styles.modelPlaceholder}>
              <svg width="30" height="30" viewBox="0 0 32 32" fill="none" aria-hidden="true" focusable="false">
                <path d="M11 5H7a2 2 0 0 0-2 2v4m16-6h4a2 2 0 0 1 2 2v4M5 21v4a2 2 0 0 0 2 2h4m16-6v4a2 2 0 0 1-2 2h-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                <path d="m10 19 4-6 4 4 4-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p>{model.placeholder}</p>
            </div>
            <div className={styles.modelOutputs}><span>Planned outputs</span><ul>{model.outputs.map(output => <li key={output}>{output}</li>)}</ul></div>
          </article>
        ))}
      </div>
      <p className={styles.pipelineNote}>Dated wound images build the timeline for these models. Each model result will be linked to the visit that produced it.</p>
    </section>
  );
}
