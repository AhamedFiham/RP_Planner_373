'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { ArrowRight, Images, ScanLine } from 'lucide-react';
import PrivateImage from './PrivateImage';
import styles from './comparison.module.css';

const dateLabel = value => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
const percent = value => Number.isFinite(value) ? `${value.toFixed(1)}%` : '\u2014';
const changeLabel = value => Number.isFinite(value) ? `${value > 0 ? '+' : ''}${value.toFixed(1)} pp` : '\u2014';
const statusLabel = status => ({ ready: 'Analyzed', no_wound: 'No wound detected', failed: 'Analysis failed', unavailable: 'Unavailable', pending: 'Needs analysis' }[status] || 'Needs analysis');

function CompositionBar({ point, tissues }) {
  return <div className={styles.composition}>
    <div className={styles.compositionLabel}><span>Tissue composition</span><span>{point.status === 'ready' ? '100% of wound mask' : 'Awaiting results'}</span></div>
    <div className={styles.compositionBar} role="img" aria-label={point.status === 'ready' ? tissues.map(tissue => `${tissue.label}: ${percent(point.percentages?.[tissue.key])}`).join(', ') : 'No tissue percentages available'}>
      {point.status === 'ready' && tissues.map(tissue => {
        const value = point.percentages?.[tissue.key];
        return Number.isFinite(value) && value > 0 ? <span key={tissue.key} style={{ width: `${value}%`, background: tissue.color }} title={`${tissue.label}: ${percent(value)}`} /> : null;
      })}
    </div>
  </div>;
}

function VisitPanel({ point, title, selectId, points, selectedId, disabledOptions, disabled, onSelect, onChooseImage, onInspectVisit, tissues, token }) {
  const image = point?.images?.find(item => item.id === point.image_id);
  const artifactId = point?.analysis?.tissue?.artifact_id;
  return <section className={styles.visitPanel} aria-labelledby={`${selectId}-heading`}>
    <div className={styles.visitHeading}>
      <h3 id={`${selectId}-heading`}>{title}</h3>
      {point && <span className={point.status === 'ready' ? styles.ready : styles.pending}>{statusLabel(point.status)}</span>}
    </div>
    <label className={styles.field} htmlFor={selectId}>Visit date
      <select id={selectId} value={selectedId} disabled={disabled || !selectedId} onChange={event => onSelect(event.target.value)}>
        {!selectedId && <option value="">Record another visit to compare</option>}
        {points.map(item => <option key={item.visit_id} value={item.visit_id} disabled={disabledOptions(item)}>{dateLabel(item.visit_date)}{item.status === 'ready' ? ' · Analyzed' : ''}</option>)}
      </select>
    </label>
    {point ? <>
      <label className={styles.field}>Photo used for comparison
        <select value={point.image_id || ''} disabled={disabled || !onChooseImage || !point.images?.length} onChange={event => onChooseImage(point, event.target.value)}>
          {!point.images?.length && <option value="">No photo uploaded</option>}
          {point.images?.map(item => <option key={item.id} value={item.id}>{item.filename}</option>)}
        </select>
      </label>
      <div className={styles.photoGrid}>
        <figure>
          {image ? <PrivateImage key={`original-${image.id}`} image={image} token={token} className={styles.photo} alt={`Original wound photograph from ${dateLabel(point.visit_date)}`} /> : <div className={styles.photo}><Images size={22} aria-hidden="true" /><span>Upload a visit photo</span></div>}
          <figcaption>Original photo</figcaption>
        </figure>
        <figure>
          {image && artifactId ? <PrivateImage key={artifactId} image={image} token={token} resourcePath={`/analysis-artifacts/${artifactId}`} className={`${styles.photo} ${styles.mask}`} alt={`Tissue segmentation mask from ${dateLabel(point.visit_date)}`} /> : <div className={`${styles.photo} ${styles.mask}`}><ScanLine size={22} aria-hidden="true" /><span>{point.status === 'no_wound' ? 'No wound foreground' : 'Run segmentation to view mask'}</span></div>}
          <figcaption>Tissue mask</figcaption>
        </figure>
      </div>
      <CompositionBar point={point} tissues={tissues} />
      {point.reason && <p className={styles.reason}>{point.reason}</p>}
      {point.analysis?.tissue?.model_version && <p className={styles.version}>Model version: {point.analysis.tissue.model_version}</p>}
      {onInspectVisit && <button className={styles.textButton} type="button" disabled={disabled} onClick={() => onInspectVisit(point.visit_id)}>Open visit <ArrowRight size={13} aria-hidden="true" /></button>}
    </> : <div className={styles.nextVisit}><Images size={28} aria-hidden="true" /><h4>Add the next visit</h4><p>Record a second visit for this wound to compare its tissue composition over time.</p></div>}
  </section>;
}

export default function TissueComparison({ progress, loading = false, error = '', onRetry, token, onChooseImage, onAnalyze, analyzing = false, analysisMessage = '', onInspectVisit }) {
  const panelId = useId();
  const [selection, setSelection] = useState({ baseline: '', followup: '' });
  const [saving, setSaving] = useState(false);
  const [selectionError, setSelectionError] = useState('');
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const points = [...(progress?.points || [])].sort((a, b) => a.visit_date.localeCompare(b.visit_date) || a.visit_id.localeCompare(b.visit_id));
  const tissues = progress?.tissues || [];
  const ready = points.filter(point => point.status === 'ready' && point.percentages);
  const defaultBaseline = ready.length > 1 ? ready[0] : points[0];
  const defaultFollowup = ready.length > 1 ? ready.at(-1) : points.length > 1 ? points.at(-1) : null;
  const baseline = points.find(point => point.visit_id === selection.baseline) || defaultBaseline;
  const baselineIndex = points.indexOf(baseline);
  const selectedFollowup = points.find(point => point.visit_id === selection.followup);
  const followup = selectedFollowup && points.indexOf(selectedFollowup) > baselineIndex ? selectedFollowup : defaultFollowup && points.indexOf(defaultFollowup) > baselineIndex ? defaultFollowup : points[baselineIndex + 1];
  const followupIndex = points.indexOf(followup);
  const comparable = baseline && followup && baseline.status === 'ready' && followup.status === 'ready' && baseline.percentages && followup.percentages;
  const needsAnalysis = [baseline, followup].filter(point => point?.image_id && point.status !== 'ready');
  const busy = loading || analyzing || saving;
  const missingPhotos = [baseline, followup].filter(point => point && !point.image_id);
  const intermediateMissing = comparable ? points.slice(baselineIndex + 1, followupIndex).filter(point => point.status !== 'ready').length : 0;

  async function chooseImage(point, imageId) {
    if (busy || !onChooseImage) return;
    setSaving(true); setSelectionError('');
    try { await onChooseImage(point.visit_id, imageId); }
    catch (failure) { if (mounted.current) setSelectionError(failure.message || 'Could not save the selected photo.'); }
    finally { if (mounted.current) setSaving(false); }
  }

  async function analyzeSelected() {
    if (busy || !onAnalyze || !needsAnalysis.length) return;
    setSelectionError('');
    try { await onAnalyze({ visitIds: needsAnalysis.map(point => point.visit_id) }); }
    catch (failure) { if (mounted.current) setSelectionError(failure.message || 'Could not analyze the selected visits.'); }
  }

  return <section className={styles.panel} aria-labelledby={`${panelId}-heading`} aria-busy={busy}>
    <div className={styles.header}>
      <div><p className={styles.eyebrow}>Visit comparison</p><h2 id={`${panelId}-heading`}>Tissue comparison across visits</h2><p className={styles.subtitle}>Compare the selected photos, masks, and tissue proportions for the same wound.</p></div>
      <span className={styles.count}>{ready.length} / {points.length} visits analyzed</span>
    </div>
    {error ? <div className={styles.alert} role="alert"><p>{error}</p><button type="button" onClick={onRetry}>Retry loading comparison</button></div> : loading ? <div className={styles.loading} role="status">Loading visit comparison…</div> : !points.length ? <div className={styles.empty}><Images size={30} aria-hidden="true" /><h3>Start with this wound’s first visit</h3><p>Record a visit and upload a wound photo. This workspace will compare tissue segmentation between the visits you choose.</p></div> : <>
      <div className={styles.visitGrid}>
        <VisitPanel title="Earlier visit" selectId={`${panelId}-baseline`} points={points} point={baseline} selectedId={baseline?.visit_id || ''} disabledOptions={point => points.indexOf(point) >= followupIndex && points.length > 1} disabled={busy} onSelect={id => setSelection({ baseline: id, followup: followup?.visit_id || '' })} onChooseImage={chooseImage} onInspectVisit={onInspectVisit} tissues={tissues} token={token} />
        <VisitPanel title="Later visit" selectId={`${panelId}-followup`} points={points} point={followup} selectedId={followup?.visit_id || ''} disabledOptions={point => points.indexOf(point) <= baselineIndex} disabled={busy} onSelect={id => setSelection({ baseline: baseline?.visit_id || '', followup: id })} onChooseImage={chooseImage} onInspectVisit={onInspectVisit} tissues={tissues} token={token} />
      </div>
      <div className={styles.actions}>
        <div><strong>{comparable ? `${dateLabel(baseline.visit_date)} → ${dateLabel(followup.visit_date)}` : points.length < 2 ? 'One visit recorded' : 'Prepare the selected visits'}</strong><p>{comparable ? 'Both visits use the selected model. Changes below are shown in percentage points (pp).' : missingPhotos.length ? 'Upload a photo for each selected visit before analyzing.' : needsAnalysis.length ? 'Run wound and tissue segmentation for the selected photos to fill this comparison.' : 'Record and analyze another visit to compare tissue proportions.'}</p></div>
        {!!needsAnalysis.length && onAnalyze && <button className={styles.analyzeButton} type="button" disabled={busy || !progress?.model_id || !token} onClick={analyzeSelected}><ScanLine size={15} aria-hidden="true" />{analyzing ? 'Analyzing visits…' : 'Analyze selected visits'}</button>}
      </div>
      {(selectionError || analysisMessage || saving) && <p className={selectionError ? styles.alert : styles.message} role={selectionError ? 'alert' : 'status'}>{selectionError || (saving ? 'Saving the photo selection…' : analysisMessage)}</p>}
      <section className={styles.results} aria-labelledby={`${panelId}-results`}>
        <div className={styles.resultsHeading}><div><h3 id={`${panelId}-results`}>Tissue composition change</h3><p>Percentage of pixels inside each photo’s wound mask.</p></div><span>Earlier → Later</span></div>
        <div className={styles.tableWrap}><table className={styles.table}>
          <caption className={styles.srOnly}>Tissue percentages in the earlier and later selected visits, and the difference in percentage points. A dash means a comparable result is unavailable.</caption>
          <thead><tr><th scope="col">Tissue type</th><th scope="col">Earlier visit</th><th scope="col">Later visit</th><th scope="col">Change</th><th scope="col" className={styles.barColumn}>Proportions</th></tr></thead>
          <tbody>{tissues.map(tissue => {
            const before = baseline?.status === 'ready' ? baseline.percentages?.[tissue.key] : null;
            const after = followup?.status === 'ready' ? followup.percentages?.[tissue.key] : null;
            const difference = comparable && Number.isFinite(before) && Number.isFinite(after) ? after - before : null;
            return <tr key={tissue.key}>
              <th scope="row"><span className={styles.tissueName}><i style={{ background: tissue.color }} aria-hidden="true" />{tissue.label}</span></th>
              <td>{percent(before)}</td><td>{percent(after)}</td><td><span className={styles.change}>{changeLabel(difference)}</span></td>
              <td className={styles.barColumn}><div className={styles.pairedBars} aria-hidden="true"><div><span style={{ width: `${Number.isFinite(before) ? before : 0}%`, background: tissue.color, opacity: .45 }} /></div><div><span style={{ width: `${Number.isFinite(after) ? after : 0}%`, background: tissue.color }} /></div></div></td>
            </tr>;
          })}</tbody>
        </table></div>
        {!!intermediateMissing && <p className={styles.note}>{intermediateMissing} intervening {intermediateMissing === 1 ? 'visit has' : 'visits have'} no comparable tissue result. The comparison uses only the two selected visits.</p>}
        <p className={styles.note}>“Unclassified” is tissue background within the wound mask. Fibrin is unavailable in these trained models.</p>
      </section>
      <p className={styles.notice}>Tissue proportions describe composition, not wound size or healing percentage. Changes in composition alone do not establish whether a wound is healing.</p>
    </>}
  </section>;
}
