import { Stethoscope } from 'lucide-react';
export default function EyeCareGuidance({ result }) {
  return <section className="retino-card retino-guidance-card" aria-labelledby="guidance-title">
    <div className="retino-card-heading"><div className="retino-icon teal"><Stethoscope size={20} /></div><div><h2 id="guidance-title">Eye-Care Guidance</h2><p>Non-diagnostic research information.</p></div></div>
    <div className="retino-guidance-review"><Stethoscope size={20} /><div><strong>Professional review</strong><p>{result.guidance?.message || 'Guidance is unavailable. Consult a qualified eye-care professional.'}</p></div></div>
    <p className="retino-guidance-note">AI-assisted retinal screening results are intended for research and decision support and do not replace professional medical assessment.</p>
  </section>;
}
