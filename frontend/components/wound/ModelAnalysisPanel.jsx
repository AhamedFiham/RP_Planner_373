'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { Play, RefreshCw } from 'lucide-react';
import PrivateImage from './PrivateImage';
import { woundRequest } from '@/lib/wound-api';
import styles from './analysis.module.css';

const stages = [
  { key: 'wound_segmentation', number: '01', title: 'Wound segmentation', description: 'Generate a segmentation mask for this wound image.' },
  { key: 'tissue_segmentation', number: '02', title: 'Tissue segmentation', description: 'Generate the tissue mask using this image and its saved wound mask.' },
  { key: 'healing_analysis', number: '03', title: 'Healing process analysis', description: 'Review segmentation masks across visits once the comparison method is defined.' },
];

function dateLabel(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function ModelAnalysisPanel({ visit, visits = [], onSelectVisit, token }) {
  const panelId = useId();
  const [imageId, setImageId] = useState('');
  const [modelId, setModelId] = useState('');
  const [modelChoices, setModelChoices] = useState([]);
  const [models, setModels] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const image = visit?.images?.find(item => item.id === imageId) || visit?.images?.[0];
  const selectedModelId = modelId || models?.selected_model_id || '';
  const scope = `${token || ''}:${image?.id || ''}:${selectedModelId}`;
  const currentScope = useRef(scope);
  currentScope.current = scope;
  const mounted = useRef(false);

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    setModels(null);
    if (!token) return;
    const controller = new AbortController();
    woundRequest(`/models${modelId ? `?model_id=${encodeURIComponent(modelId)}` : ''}`, token, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) { setModels(result); setModelChoices(result.models || []); } })
      .catch(error => { if (!controller.signal.aborted) setError(error.message); });
    return () => controller.abort();
  }, [token, revision, modelId]);

  useEffect(() => {
    setRuns([]); setError(''); setBusy('');
    if (!token || !image) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    woundRequest(`/images/${image.id}/analysis`, token, { signal: controller.signal })
      .then(result => { if (!controller.signal.aborted) setRuns(result); })
      .catch(error => { if (!controller.signal.aborted) setError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, image?.id, revision]);

  const selectedRuns = runs.filter(run => (run.model_id || 'default') === selectedModelId);
  const woundRun = selectedRuns.find(run => run.stage === 'wound_segmentation' && run.status === 'completed');
  async function analyze(stage) {
    if (!image || busy) return;
    const requestScope = scope;
    setBusy(stage); setError('');
    try {
      const result = await woundRequest(`/images/${image.id}/analysis`, token, { method: 'POST', body: { stage, model_id: selectedModelId || undefined } });
      if (!mounted.current || currentScope.current !== requestScope) return;
      setRuns(items => [result, ...items.filter(item => item.id !== result.id)]);
      const updatedModels = await woundRequest(`/models${selectedModelId ? `?model_id=${encodeURIComponent(selectedModelId)}` : ''}`, token);
      if (mounted.current && currentScope.current === requestScope) setModels(updatedModels);
    } catch (error) {
      if (mounted.current && currentScope.current === requestScope) setError(error.message);
    } finally {
      if (mounted.current && currentScope.current === requestScope) setBusy('');
    }
  }

  return <section className={styles.panel} aria-labelledby={`${panelId}-heading`}>
    <div className={styles.panelHeader}>
      <div><p className={styles.eyebrow}>Analysis pipeline</p><h2 id={`${panelId}-heading`} className={styles.heading}>Wound and tissue segmentation</h2><p className={styles.subtitle}>Choose a model, visit, and image to review saved masks.</p></div>
      <button type="button" className={styles.refreshButton} onClick={() => setRevision(value => value + 1)} disabled={!!busy || loading} aria-label="Refresh model availability and results"><RefreshCw size={14} /> Refresh</button>
    </div>
    <div className={styles.analysisSelection}>
      <label htmlFor={`${panelId}-model`}>Segmentation model<select id={`${panelId}-model`} value={selectedModelId} onChange={event => setModelId(event.target.value)} disabled={!modelChoices.length || !!busy}>
        {!modelChoices.length && <option value="">Models not configured</option>}
        {modelChoices.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select></label>
      <label htmlFor={`${panelId}-visit`}>Visit<select id={`${panelId}-visit`} value={visit?.id || ''} onChange={event => { setImageId(''); onSelectVisit?.(event.target.value); }} disabled={!visits.length || !!busy}>
        {!visits.length && <option value="">No visits recorded</option>}
        {visits.map(item => <option key={item.id} value={item.id}>{dateLabel(item.visit_date)}</option>)}
      </select></label>
      <label htmlFor={`${panelId}-image`}>Wound image<select id={`${panelId}-image`} value={image?.id || ''} onChange={event => setImageId(event.target.value)} disabled={!image || !!busy}>
        {!image && <option value="">No image selected</option>}
        {visit?.images?.map((item, index) => <option key={item.id} value={item.id}>{index + 1}. {item.filename}</option>)}
      </select></label>
    </div>
    {error && <div className={styles.analysisError} role="alert"><span>{error}</span><button type="button" onClick={() => setRevision(value => value + 1)} disabled={!!busy}>Try again</button></div>}
    {image && <div className={styles.sourceImage}><PrivateImage image={image} token={token} className={styles.originalPreview} alt={`Original wound photograph from ${dateLabel(visit.visit_date)}`} /><span>Original image · {image.filename}</span></div>}
    <div className={styles.modelGrid} aria-busy={loading || !!busy}>
      {stages.map(stage => {
        const history = selectedRuns.filter(run => run.stage === stage.key);
        const latest = history[0];
        const model = models?.[stage.key];
        const isHealing = stage.key === 'healing_analysis';
        const available = models?.selected_model_id === selectedModelId && ['configured', 'ready'].includes(model?.status);
        const isBusy = busy === stage.key || latest?.status === 'running';
        const needsWound = stage.key === 'tissue_segmentation' && !woundRun;
        const staleTissue = stage.key === 'tissue_segmentation' && latest?.status === 'completed' && woundRun && latest.input_analysis_id !== woundRun.id;
        const status = isHealing ? 'Method pending' : isBusy ? 'Analyzing…' : staleTissue ? 'Needs rerun' : latest?.status === 'completed' ? 'Completed' : latest?.status === 'failed' ? 'Failed' : available ? 'Available' : models ? 'Not connected' : 'Checking…';
        const helper = isHealing ? 'The healing method and graph will be added after the comparison requirements are provided.' : !image ? 'Record a visit image to begin.' : !available ? 'Waiting for the trained model and inference code.' : needsWound ? 'Run wound segmentation on this image first.' : latest?.status === 'failed' ? latest.error || 'Analysis failed. You can retry this image.' : 'Run analysis to generate and save this image’s mask.';
        return <article className={styles.modelCard} key={stage.key}>
          <div className={styles.modelTop}><span className={styles.modelNumber}>{stage.number}</span><span className={styles.modelStatus}>{status}</span></div>
          <h3>{stage.title}</h3><p className={styles.modelDescription}>{stage.description}</p>
          {latest?.status === 'completed' && latest.artifacts?.length ? <div className={styles.resultImages}>{latest.artifacts.map(artifact => <figure key={artifact.id}><PrivateImage image={artifact} token={token} resourcePath={`/analysis-artifacts/${artifact.id}`} className={styles.maskPreview} alt={`${stage.title} ${artifact.kind} for the selected visit image`} /><figcaption>{artifact.kind === 'mask' ? 'Segmentation mask' : 'Image overlay'}</figcaption></figure>)}</div> : <div className={styles.modelPlaceholder}><p>{isBusy ? 'Processing the selected image. Results will be saved with this visit.' : helper}</p></div>}
          {staleTissue && <p className={styles.rerunNote}>A newer wound mask is available. Rerun tissue segmentation to use it.</p>}
          {latest?.model_version && <p className={styles.version}>Result model version: {latest.model_version}</p>}
          {latest?.status === 'completed' && ['unet_resnet18', 'deeplabv3plus_mobilenet_v2', 'segformer_mit_b0'].includes(selectedModelId) && (stage.key === 'wound_segmentation' ? <p className={styles.version}>White: predicted wound mask. Black: background.</p> : stage.key === 'tissue_segmentation' ? <div className={styles.tissueLegend}>{[['#ff66cc','Epithelialization'],['#ff0000','Granulation'],['#808080','Slough'],['#8b4513','Necrosis'],['#00ffff','Bone/tendon/muscle'],['#00b050','Other']].map(([color, label]) => <span key={label}><i style={{ background: color }} />{label}</span>)}<p>Fibrin is unavailable in these trained checkpoints.</p></div> : null)}
          {!isHealing && <button type="button" className={styles.analyzeButton} onClick={() => analyze(stage.key)} disabled={!token || !image || !available || needsWound || !!busy || loading || latest?.status === 'running'}><Play size={13} />{isBusy ? 'Analyzing…' : latest ? 'Run again' : 'Analyze image'}</button>}
          {!!history.length && <details className={styles.runHistory}><summary>Analysis history ({history.length})</summary><ol>{history.map(run => <li key={run.id}><strong>{run.status}</strong><span>{run.model_version || 'Version unavailable'}</span><time dateTime={run.created_at}>{new Date(run.created_at).toLocaleString()}</time></li>)}</ol></details>}
        </article>;
      })}
    </div>
    <p className={styles.pipelineNote}>Original images are preserved. Each result is saved against its exact visit image. The healing graph remains empty.</p>
  </section>;
}
