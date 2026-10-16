import { BarChart3 } from 'lucide-react';
import { RETINOPATHY_SEVERITIES, percent } from '@/lib/retinopathy/constants';

export default function SeverityProbabilityChart({ result }) {
  return (
    <section className="retino-card" aria-labelledby="probability-title">
      <div className="retino-card-heading"><div className="retino-icon blue"><BarChart3 size={20} /></div><div><h2 id="probability-title">Severity Probability Distribution</h2><p>{result.calibrated === true && !result.isDemo ? "Calibrated Probabilities" : "Uncalibrated Probabilities"}</p></div></div>
      <div className="retino-bars">{RETINOPATHY_SEVERITIES.map((item, index) => <div className={`retino-bar-row ${index === result.predictedClass ? 'selected' : ''}`} key={item.key}><span className="retino-bar-label">{item.label}</span><div className="retino-bar-track"><span style={{ width: `${percent(result.probabilities[index])}`, background: item.color }} /></div><strong>{percent(result.probabilities[index])}</strong></div>)}</div>
      <p className="retino-chart-note">{result.calibrated === true && !result.isDemo
        ? 'The backend identifies these probabilities as calibrated. They express relative model confidence across classes, not certainty of a clinical diagnosis.'
        : 'These are raw model probabilities, not calibrated confidence or certainty of a clinical diagnosis.'}</p>
    </section>
  );
}
