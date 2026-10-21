import { CircleAlert, ScanEye, Upload } from 'lucide-react';
import { percent } from '@/lib/retinopathy/constants';
export default function ImageQualityAssessment({ quality, onUploadAnother }) {
  if (!quality) return null;
  const rejected = quality.label === 'Unacceptable' && quality.gate === 'reupload';
  return <section className={`retino-card retino-quality-card ${rejected ? 'is-rejected' : ''}`} aria-labelledby="quality-title">
    <div className="retino-card-heading"><div className={`retino-icon ${rejected ? 'red' : 'blue'}`}>{rejected ? <CircleAlert size={20} /> : <ScanEye size={20} />}</div><div><h2 id="quality-title">Image Quality Assessment</h2><p>Quality gate reported by the backend.</p></div><span className={`retino-status-badge ${quality.label.toLowerCase()}`}>{quality.label}</span></div>
    <div className="retino-quality-body"><div className="retino-quality-overall"><strong>{rejected ? 'Unacceptable — replacement image required' : 'Acceptable — image quality accepted'}</strong><p>{rejected ? 'Please upload a clearer retinal image. Severity analysis was not performed.' : `Quality confidence: ${percent(quality.confidence)}`}</p></div><div className="retino-quality-metrics">{Object.entries(quality.probabilities || {}).map(([label,value]) => <div key={label}><span>{label}</span><strong className={label === 'Unacceptable' ? 'bad' : ''}>{percent(value)}</strong></div>)}</div></div>
    {rejected && <button type="button" className="retino-button ghost" onClick={onUploadAnother}><Upload size={16} /> Upload Another Image</button>}
    {/* <p className="retino-micro-note">Quality model: {quality.model_version}</p> */}
  </section>;
}
