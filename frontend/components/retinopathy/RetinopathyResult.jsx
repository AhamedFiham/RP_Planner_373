'use client';
import { CLASS_KEYS } from '@/lib/retinopathy/constants';
import useRetinopathyArtifacts from '@/hooks/useRetinopathyArtifacts';
import SeverityResult from './SeverityResult';
import SeverityProbabilityChart from './SeverityProbabilityChart';
import GradCAMVisualization from './GradCAMVisualization';
import SeverityComparison from './SeverityComparison';
import ConfidenceIndicator from './ConfidenceIndicator';
import EyeCareGuidance from './EyeCareGuidance';
export default function RetinopathyResult({ result, api }) {
  const images = useRetinopathyArtifacts(api, result.gradcam);
  const view = { ...result, gradcam: CLASS_KEYS.map(key => ({ heatmapUrl: images.urls[result.gradcam?.artifacts?.[key]?.heatmap], overlayUrl: images.urls[result.gradcam?.artifacts?.[key]?.overlay] })) };
  return <div className="retino-results" aria-live="polite">
    <div className="retino-section-label"><span>{result.historical ? 'SAVED ASSESSMENT' : 'RESEARCH ANALYSIS'}</span><span className="retino-section-line" /></div>
    <p className="retino-chart-note">{result.historical ? 'Assessment date' : 'Response received'}: {new Date(result.receivedAt).toLocaleString()} · {result.assessmentId ? 'Saved assessment' : 'Not saved to history'} · Model: {result.modelVersion}</p>
    <div className="retino-result-grid"><SeverityResult result={view} /><SeverityProbabilityChart result={view} /></div>
    {images.loading && <p role="status">Loading protected retinal images…</p>}{images.error && <p role="alert" className="retino-error">{images.error}</p>}
    {!result.gradcam?.available && <p role="status" className="retino-error">Grad-CAM explanations are unavailable for this assessment.</p>}
    <GradCAMVisualization imageUrl={images.urls[result.gradcam?.original]} gradcam={view.gradcam[result.predictedClass]} />
    {/* <SeverityComparison key={result.assessmentId || result.receivedAt} result={view} /> */}
    {/* <div className="retino-result-grid"><ConfidenceIndicator result={view} /><EyeCareGuidance result={view} /></div> */}
    {result.disclaimer && <p className="retino-result-disclaimer">{result.disclaimer}</p>}
  </div>;
}
