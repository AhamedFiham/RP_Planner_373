import { Eye, Info, Layers3 } from 'lucide-react';
import AttentionPreview from './AttentionPreview';

export default function GradCAMVisualization({ imageUrl, gradcam }) {
  return (
    <section className="retino-card" aria-labelledby="gradcam-title">
      <div className="retino-card-heading">
        <div className="retino-icon purple"><Layers3 size={20} /></div>
        <div><h2 id="gradcam-title">Explainable AI — Grad-CAM</h2><p>Grad-CAM visualizations help illustrate which retinal regions influenced the AI model's classification.</p></div>
      </div>
      <div className="retino-visual-grid">
        <div className="retino-visual-panel"><div className="retino-visual-heading">Original retinal image</div><div className="retino-visual-frame original"><AttentionPreview imageUrl={imageUrl} label="Original retinal fundus image" /></div></div>
        <div className="retino-visual-panel"><div className="retino-visual-heading">Grad-CAM attention map</div><div className="retino-visual-frame"><AttentionPreview imageUrl={gradcam?.heatmapUrl} label="Model-generated Grad-CAM attention map" /></div></div>
        <div className="retino-visual-panel"><div className="retino-visual-heading">Grad-CAM overlay</div><div className="retino-visual-frame"><AttentionPreview imageUrl={gradcam?.overlayUrl} label="Model-generated Grad-CAM overlay" /></div></div>
      </div>
      <details className="retino-gradcam-info"><summary><Info size={15} /> How to interpret Grad-CAM</summary><p>Grad-CAM highlights image regions influencing a model's output. Highlighted areas are not necessarily confirmed retinal lesions.</p></details>
      <div className="retino-inline-info"><Eye size={15} /><span>These maps explain the current classification, not future disease progression or confirmed retinal lesions. Overlays use the model-input grid, which may differ from the original dimensions.</span></div>
    </section>
  );
}
