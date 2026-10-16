import { BrainCircuit, Info } from 'lucide-react';
import { RETINOPATHY_SEVERITIES, percent } from '@/lib/retinopathy/constants';

export default function SeverityResult({ result }) {
  const severity = RETINOPATHY_SEVERITIES[result.predictedClass];
  return (
    <section className="retino-card" aria-labelledby="severity-title">
      <div className="retino-card-heading"><div className="retino-icon orange"><BrainCircuit size={20} /></div><div><h2 id="severity-title">AI Severity Assessment</h2><p>Five-class model result for this assessment.</p></div><span className="retino-demo-pill">Research result</span></div>
      <div className="retino-result-main"><div><span className="retino-eyebrow">Predicted severity</span><strong className="retino-severity-name" style={{ color: severity.color }}>{severity.label}</strong><span className="retino-severity-full">{severity.fullLabel}</span></div><div className="retino-confidence-chip"><span>Confidence</span><strong>{percent(result.confidence)}</strong></div></div>
      <div className="retino-severity-scale" aria-label="Five class severity scale">{RETINOPATHY_SEVERITIES.map((item, index) => <div className={index === result.predictedClass ? 'active' : ''} key={item.key} title={item.description}><span className="retino-scale-dot" style={{ background: item.color }} /><span>{item.label}</span></div>)}</div>
      <div className="retino-inline-info"><Info size={15} /><span>Class {severity.classNumber} of 5. {severity.description}</span></div>
      <details className="retino-stage-guide"><summary>Understand the five stages</summary>{RETINOPATHY_SEVERITIES.map(item => <p key={item.key}><strong>{item.label}: </strong>{item.description}</p>)}</details>
      <p className="retino-result-disclaimer">This research result is not a confirmed clinical diagnosis.</p>
    </section>
  );
}
