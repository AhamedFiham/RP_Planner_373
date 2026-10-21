/*'use client';

import { Check, Maximize2 } from 'lucide-react';
import { useState } from 'react';
import { RETINOPATHY_SEVERITIES, percent } from '@/lib/retinopathy/constants';
import AttentionPreview from './AttentionPreview';

export default function SeverityComparison({ result }) {
  const [selected, setSelected] = useState(result.predictedClass);
  const severity = RETINOPATHY_SEVERITIES[selected];
  return (
    <section className="retino-card" aria-labelledby="comparison-title">
      <div className="retino-card-heading"><div className="retino-icon purple"><Maximize2 size={19} /></div><div><h2 id="comparison-title">Severity-Aware Attention Comparison</h2><p>Compare the retinal regions associated with each diabetic retinopathy severity class.</p></div></div>
      <div className="retino-comparison-grid">
        {RETINOPATHY_SEVERITIES.map((item, index) => (
          <button type="button" className={`retino-comparison-panel ${selected === index ? 'selected' : ''}`} key={item.key}
            onClick={() => setSelected(index)} aria-pressed={selected === index} aria-controls="retino-expanded-attention"
            aria-label={`Inspect ${item.label} attention, ${result.probabilities[index]} percent`}>
            <span className="retino-comparison-head"><span>{item.label}</span><strong>{percent(result.probabilities[index])}</strong></span>
            <AttentionPreview compact imageUrl={result.gradcam?.[index]?.overlayUrl} label={`${item.label} class attention`} />
            <small>{selected === index ? <><Check size={12} /> Selected class</> : index === result.predictedClass ? 'Predicted class' : 'Inspect attention'}</small>
          </button>
        ))}
      </div>
      <div id="retino-expanded-attention" className="retino-expanded-attention" aria-live="polite">
        <div><h3>{severity.label} · Class {selected}</h3><p>{percent(result.probabilities[selected])} probability</p><p>{severity.description}</p></div>
        <AttentionPreview imageUrl={result.gradcam?.[selected]?.overlayUrl} label={`Expanded ${severity.label} class attention`} />
      </div>
      <p className="retino-chart-note">The panels represent five possible model classifications for the current image; they do not imply progression of a single patient's retina.</p>
    </section>
  );
}
*/