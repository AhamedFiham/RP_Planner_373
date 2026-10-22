'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { woundRequest } from '@/lib/wound-api';
import { compareTissues } from '@/lib/wound-trends.mjs';
import PrivateImage from './PrivateImage';
import styles from './analysis.module.css';

const stages = [
  { id: 'wound_segmentation', number: '01', title: 'Wound segmentation', description: 'Generate a wound mask for the selected visit image.' },
  { id: 'tissue_segmentation', number: '02', title: 'Tissue segmentation', description: 'Identify tissue classes with the same model and wound image.' },
];
const tissueLegend = [
  ['Background', '#000000'], ['Epithelialization', '#ff66cc'], ['Granulation', '#ff0000'],
  ['Slough', '#808080'], ['Necrosis', '#8b4513'], ['Bone / tendon / muscle', '#00ffff'], ['Other', '#00b050'],
];
const available = status => status === 'configured' || status === 'ready';
const displayDate = value => value ? new Date(value.length === 10 ? `${value}T12:00:00` : value).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : '';
const maskFor = result => result?.artifacts?.find(artifact => artifact.kind === 'mask');

export default function ModelAnalysisPanel({ visit, visits = [], onSelectVisit, token, selectedModelId, onModelChange, onModelsLoaded, onAnalysisComplete, progress, progressLoading = false, progressError = '', onCompareVisits, onRefreshProgress }) {
  const panelId = useId();
  const [localModelId, setLocalModelId] = useState('');
  const modelId = selectedModelId ?? localModelId;
  const [imageSelection, setImageSelection] = useState({ visitId: '', imageId: '' });
  const images = visit?.images || [];
  const image = images.find(item => imageSelection.visitId === visit?.id && item.id === imageSelection.imageId) || images.find(item => item.id === visit?.progress_image_id) || images[0];
  const imageId = image?.id || '';
  const modelScope = `${token || ''}\0${modelId}`;
  const scope = `${modelScope}\0${imageId}`;
  const scopeRef = useRef(scope);
  scopeRef.current = scope;
  const modelScopeRef = useRef(modelScope);
  modelScopeRef.current = modelScope;
  const mountedRef = useRef(true);
  const runningRef = useRef(false);
  const [catalog, setCatalog] = useState(null);
  const [catalogError, setCatalogError] = useState('');
  const [history, setHistory] = useState({ scope: '', rows: [] });
  const [historyError, setHistoryError] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [running, setRunning] = useState(null);
  const [runError, setRunError] = useState('');
  const callbackRef = useRef({ onModelChange, onModelsLoaded, onAnalysisComplete });
  callbackRef.current = { onModelChange, onModelsLoaded, onAnalysisComplete };

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  function selectModel(id) {
    setLocalModelId(id);
    callbackRef.current.onModelChange?.(id);
  }

  useEffect(() => {
    const controller = new AbortController();
    setCatalogError('');
    if (!token) { setCatalog(null); return () => controller.abort(); }
    woundRequest(`/models${modelId ? `?model_id=${encodeURIComponent(modelId)}` : ''}`, token, { signal: controller.signal })
      .then(data => {
        if (controller.signal.aborted || modelScopeRef.current !== modelScope) return;
        setCatalog({ scope: modelScope, data });
        callbackRef.current.onModelsLoaded?.(data);
        if (!modelId && data.selected_model_id) {
          setLocalModelId(data.selected_model_id);
          callbackRef.current.onModelChange?.(data.selected_model_id);
        }
      })
      .catch(error => {
        if (error.name !== 'AbortError' && modelScopeRef.current === modelScope) {
          setCatalog(null); setCatalogError(error.message);
        }
      });
    return () => controller.abort();
  }, [token, modelId, modelScope, refresh]);

  useEffect(() => {
    const controller = new AbortController();
    setHistoryError(''); setRunError('');
    setHistory({ scope, rows: [] });
    if (!token || !imageId || !modelId) { setLoadingHistory(false); return () => controller.abort(); }
    setLoadingHistory(true);
    woundRequest(`/images/${imageId}/analysis`, token, { signal: controller.signal })
      .then(rows => {
        if (!controller.signal.aborted && scopeRef.current === scope) setHistory({ scope, rows });
      })
      .catch(error => {
        if (error.name !== 'AbortError' && scopeRef.current === scope) setHistoryError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted && scopeRef.current === scope) setLoadingHistory(false);
      });
    return () => controller.abort();
  }, [token, imageId, modelId, scope, refresh]);

  const modelData = catalog?.scope === modelScope ? catalog.data : null;
  const modelChoices = catalog?.data?.models || [];
  const rows = history.scope === scope ? history.rows.filter(row => row.model_id === modelId) : [];
  const latestWound = rows.find(row => row.stage === 'wound_segmentation' && row.status === 'completed' && maskFor(row));
  const currentRunning = running?.scope === scope ? running.stage : null;
  const trendProgress = progress?.model_id === modelId ? progress : null;
  const trendPoints = trendProgress?.points || [];
  const trendTissues = trendProgress?.tissues || [];
  const readyVisits = trendPoints.filter(point => point.status === 'ready' && point.percentages);
  const latestReadyVisit = readyVisits.at(-1);
  const visitCount = trendProgress?.summary?.visit_count ?? visits.length;
  const missingVisitCount = Math.max(0, visitCount - readyVisits.length);
  const tissueComparison = compareTissues(trendPoints, trendTissues);
  const leadingChanges = (tissueComparison?.changes || []).filter(tissue => Number.isFinite(tissue.change)).sort((a, b) => Math.abs(b.change) - Math.abs(a.change)).slice(0, 3);
  const latestComposition = latestReadyVisit ? trendTissues.filter(tissue => Number.isFinite(latestReadyVisit.percentages[tissue.key]) && latestReadyVisit.percentages[tissue.key] > 0) : [];

  async function runStage(stage) {
    if (runningRef.current || !imageId || !modelId || !token) return;
    runningRef.current = true;
    const requestScope = scope;
    setRunning({ scope: requestScope, stage }); setRunError('');
    try {
      const result = await woundRequest(`/images/${imageId}/analysis`, token, { method: 'POST', body: { stage, model_id: modelId } });
      if (!mountedRef.current || scopeRef.current !== requestScope) return;
      setHistory(previous => ({ scope: requestScope, rows: [result, ...(previous.scope === requestScope ? previous.rows.filter(row => row.id !== result.id) : [])] }));
      if (result.status === 'failed') setRunError(result.error || 'Analysis failed. Please retry.');
      if (result.status === 'completed') callbackRef.current.onAnalysisComplete?.(result);
    } catch (error) {
      if (mountedRef.current && scopeRef.current === requestScope) setRunError(error.message);
    } finally {
      runningRef.current = false;
      if (mountedRef.current) setRunning(previous => previous?.scope === requestScope ? null : previous);
    }
  }

  return (
    <section className={styles.panel} aria-labelledby={`${panelId}-heading`}>
      <div className={styles.panelHeader}>
        <div>
          <p className={styles.eyebrow}>Image analysis</p>
          <h2 id={`${panelId}-heading`} className={styles.heading}>Wound and tissue segmentation</h2>
          <p className={styles.subtitle}>Choose a model, then analyse each visit image. Saved tissue masks contribute to the visit timeline.</p>
        </div>
        <button className={styles.analysisRefresh} type="button" onClick={() => { setRefresh(value => value + 1); onRefreshProgress?.(); }} disabled={Boolean(running)} aria-label="Refresh model status, saved analysis, and tissue trends">Refresh</button>
      </div>
      <div className={styles.analysisSelectors}>
        <label htmlFor={`${panelId}-model`}>Segmentation model
          <select id={`${panelId}-model`} value={modelId} onChange={event => selectModel(event.target.value)} disabled={!modelChoices.length || Boolean(running)}>
            {!modelChoices.length && <option value="">{catalogError ? 'Models unavailable' : 'Loading models...'}</option>}
            {modelChoices.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
          </select>
        </label>
        {onSelectVisit && <label htmlFor={`${panelId}-visit`}>Visit
          <select id={`${panelId}-visit`} value={visit?.id || ''} onChange={event => onSelectVisit(event.target.value)} disabled={!visits.length || Boolean(running)}>
            {!visits.length && <option value="">No recorded visits</option>}
            {visits.map(item => <option key={item.id} value={item.id}>{displayDate(item.visit_date)}</option>)}
          </select>
        </label>}
        <label htmlFor={`${panelId}-image`}>Visit image
          <select id={`${panelId}-image`} value={imageId} onChange={event => setImageSelection({ visitId: visit.id, imageId: event.target.value })} disabled={!images.length || Boolean(running)}>
            {!images.length && <option value="">Select a visit with images</option>}
            {images.map((item, index) => <option key={item.id} value={item.id}>{index + 1}. {item.filename}</option>)}
          </select>
        </label>
      </div>
      {(catalogError || historyError || runError) && <div className={styles.analysisError} role="alert">{catalogError || historyError || runError}</div>}
      {loadingHistory && <p className={styles.analysisMessage} role="status">Loading saved analysis...</p>}
      <div className={styles.modelGrid}>
        {stages.map(stage => {
          const latest = rows.find(row => row.stage === stage.id);
          const result = rows.find(row => row.stage === stage.id && row.status === 'completed' && maskFor(row));
          const artifact = maskFor(result);
          const isRunning = currentRunning === stage.id || latest?.status === 'running';
          const canRun = available(modelData?.[stage.id]?.status);
          const needsWound = stage.id === 'tissue_segmentation' && !latestWound;
          const staleTissue = stage.id === 'tissue_segmentation' && result && latestWound && result.input_analysis_id !== latestWound.id;
          const status = isRunning ? 'Processing' : latest?.status === 'failed' ? 'Failed' : artifact ? 'Saved mask' : canRun ? 'Ready to run' : modelData ? 'Unavailable' : 'Checking model';
          return <article key={stage.id} className={styles.modelCard} aria-busy={isRunning}>
            <div className={styles.modelTop}><span className={styles.modelNumber}>{stage.number}</span><span className={styles.modelStatus}>{status}</span></div>
            <h3>{stage.title}</h3><p className={styles.modelDescription}>{stage.description}</p>
            {artifact ? <div className={styles.analysisMaskWrap}>
              <PrivateImage image={{ id: artifact.id, filename: `${stage.title} mask` }} resourcePath={`/analysis-artifacts/${artifact.id}`} token={token} className={styles.analysisMask} alt={`${stage.title} mask for ${image?.filename || 'selected image'}`} />
              <p className={styles.analysisVersion}>Saved {displayDate(result.completed_at)} · {result.model_version}</p>
            </div> : <div className={styles.modelPlaceholder}><p>{isRunning ? 'The model is processing this image.' : image ? 'Run analysis to generate the mask for this image.' : 'Select a recorded visit and image to begin.'}</p></div>}
            {staleTissue && <p className={styles.analysisMessage}>This tissue result uses an earlier wound mask. Run tissue segmentation again to update the timeline.</p>}
            {latest?.status === 'failed' && <p className={styles.analysisStageError}>{latest.error || 'The latest analysis failed. Retry to generate a mask.'}</p>}
            <button type="button" className={styles.analysisRun} onClick={() => runStage(stage.id)} disabled={!image || !modelId || !canRun || Boolean(running) || loadingHistory || Boolean(historyError) || isRunning || needsWound}>
              {isRunning ? 'Processing...' : latest?.status === 'failed' ? 'Retry analysis' : artifact ? 'Run analysis again' : 'Run analysis'}
            </button>
            {needsWound && image && <p className={styles.analysisMessage}>Run wound segmentation for this image and model first.</p>}
            {!canRun && modelData && <p className={styles.analysisMessage}>The selected model is unavailable. Check the model service and server configuration.</p>}
            {artifact && <div className={styles.analysisLegend} aria-label={`${stage.title} colour key`}>
              {(stage.id === 'tissue_segmentation' ? tissueLegend : [['Background', '#000000'], ['Wound', '#ffffff']]).map(([label, colour]) => <span key={label}><i style={{ backgroundColor: colour }} aria-hidden="true" />{label}</span>)}
            </div>}
            {artifact && stage.id === 'tissue_segmentation' && <p className={styles.analysisMessage}>Fibrin is excluded because these checkpoints were not trained on that class.</p>}
          </article>;
        })}
        <article className={styles.modelCard} aria-busy={progressLoading}>
          <div className={styles.modelTop}><span className={styles.modelNumber}>03</span><span className={styles.modelStatus}>{progressLoading ? 'Loading trends' : progressError ? 'Unable to load' : `${readyVisits.length} / ${visitCount} visits analyzed`}</span></div>
          <h3>Tissue trends across visits</h3>
          <p className={styles.modelDescription}>Compare tissue proportions across dated visits using the same segmentation model.</p>
          {progressError ? <p className={styles.comparisonCardError} role="alert">{progressError}</p> : progressLoading ? <div className={styles.comparisonCardLoading} role="status"><span /><span /><span /><p>Loading saved tissue results...</p></div> : <div className={styles.comparisonCardBody}>
            {latestReadyVisit ? <>
              <div className={styles.comparisonCardDates}>
                <span>{tissueComparison ? 'First analyzed visit' : 'Analyzed visit'}<strong>{displayDate(readyVisits[0].visit_date)}</strong></span>
                {tissueComparison && <span>Latest analyzed visit<strong>{displayDate(latestReadyVisit.visit_date)}</strong></span>}
              </div>
              <p className={styles.comparisonCardCaption}>Latest tissue composition</p>
              <div className={styles.comparisonCardStack} role="img" aria-label={`Tissue composition for ${displayDate(latestReadyVisit.visit_date)}: ${latestComposition.map(tissue => `${tissue.label} ${latestReadyVisit.percentages[tissue.key].toFixed(1)} percent`).join(', ')}`}>
                {latestComposition.map(tissue => <span key={tissue.key} style={{ width: `${latestReadyVisit.percentages[tissue.key]}%`, background: tissue.color }} title={`${tissue.label}: ${latestReadyVisit.percentages[tissue.key].toFixed(1)}%`} />)}
              </div>
              {tissueComparison ? <><p className={styles.comparisonCardCaption}>Largest changes since first analyzed visit</p><ul className={styles.comparisonCardChanges}>
                {leadingChanges.map(tissue => <li key={tissue.key}><span><i style={{ background: tissue.color }} aria-hidden="true" />{tissue.label}</span><strong>{tissue.change > 0 ? '+' : ''}{tissue.change.toFixed(1)} pp</strong></li>)}
              </ul><p className={styles.analysisMessage}>pp = percentage points. Compare visits to see all tissues and photos.</p></> : <p className={styles.analysisMessage}>Analyze another visit to compare tissue proportions over time.</p>}
            </> : <p className={styles.comparisonCardEmpty}>{visitCount ? 'Run wound and tissue segmentation for each visit’s selected photo to build the comparison.' : 'Record visits with wound images to start a tissue comparison.'}</p>}
            {missingVisitCount > 0 && <p className={styles.analysisMessage}>{missingVisitCount} {missingVisitCount === 1 ? 'visit has' : 'visits have'} no comparable tissue result for this model.</p>}
          </div>}
          <button type="button" className={`${styles.analysisRun} ${styles.comparisonCardButton}`} onClick={() => onCompareVisits?.()} disabled={visits.length < 2 || !onCompareVisits}>{visits.length < 2 ? 'Add a follow-up visit to compare' : 'Compare visits'}</button>
          <p className={styles.analysisMessage}>Tissue percentages describe the masks. A healing percentage will be added after its calculation method is defined.</p>
        </article>
      </div>
      {rows.length > 0 && <details className={styles.analysisHistory}>
        <summary>Saved analysis history ({rows.length})</summary>
        <div className={styles.tableWrap}><table className={styles.table}>
          <thead><tr><th scope="col">Stage</th><th scope="col">Status</th><th scope="col">Date</th><th scope="col">Model version</th></tr></thead>
          <tbody>{rows.map(row => <tr key={row.id}><td>{row.stage === 'wound_segmentation' ? 'Wound segmentation' : 'Tissue segmentation'}</td><td>{row.status}</td><td>{displayDate(row.completed_at || row.created_at)}</td><td>{row.model_version}</td></tr>)}</tbody>
        </table></div>
      </details>}
      <p className={styles.pipelineNote}>Masks and analysis history are stored privately with the selected image and model. Image pixel counts do not measure physical wound size.</p>
    </section>
  );
}
