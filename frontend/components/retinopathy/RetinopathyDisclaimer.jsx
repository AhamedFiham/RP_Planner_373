import { Info } from 'lucide-react';

export default function RetinopathyDisclaimer() {
  return <aside className="retino-disclaimer" aria-label="Research and medical disclaimer"><Info size={18} /><p>This AI-assisted retinal screening module is developed for academic research and decision-support purposes. Its outputs are not a medical diagnosis and should not replace assessment by a qualified eye-care professional.</p></aside>;
}
