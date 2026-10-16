import { TriangleAlert } from 'lucide-react';
import { percent, RETINOPATHY_SEVERITIES } from '@/lib/retinopathy/constants';
export default function ConfidenceIndicator({ result }) {
  return <section className="retino-card retino-confidence-card uncertain" aria-labelledby="confidence-title">
    <div className="retino-card-heading"><div className="retino-icon orange"><TriangleAlert size={20} /></div><div><h2 id="confidence-title">Prediction Confidence &amp; Reliability</h2><p>Backend reliability assessment.</p></div></div>
    <div className="retino-confidence-summary"><div><span className="retino-eyebrow">Top predicted class</span><strong>{RETINOPATHY_SEVERITIES[result.predictedClass].label}</strong></div><div className="retino-confidence-number">{percent(result.confidence)}<small>{result.reliability?.requires_review !== false ? 'Professional review recommended' : result.reliability.status}</small></div></div>
    <div className="retino-reliability-list"><div><span>Image quality</span><strong>{result.quality}</strong></div><div><span>Calibration</span><strong>{result.calibrated ? 'Calibrated' : 'Uncalibrated'}</strong></div><div><span>Reliability</span><strong>{result.reliability?.status || 'Unavailable'}</strong></div></div>
    <div className="retino-reliability-message">{result.reliability?.reason || 'Reliability details are unavailable. Professional review is recommended.'} Calibration does not establish clinical safety.</div>
  </section>;
}
