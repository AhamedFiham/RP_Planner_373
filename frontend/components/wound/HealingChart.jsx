'use client';

import { useId, useState } from 'react';
import { compareTissues, positionVisits, tissueSegments } from '@/lib/wound-trends.mjs';
import styles from './analysis.module.css';

const CHART = { width: 800, height: 310, left: 50, right: 25, top: 25, bottom: 55 };
const dateLabel = value => new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
const percent = value => Number.isFinite(value) ? `${value.toFixed(1)}%` : '—';
const delta = value => `${value > 0 ? '+' : ''}${value.toFixed(1)} pp`;

export default function HealingChart({ progress, loading = false, error = '', modelLabel, onRetry, onChooseImage, onSelectVisit }) {
  const chartId = useId();
  const [hidden, setHidden] = useState([]);
  const [inspectedId, setInspectedId] = useState('');
  const [savingVisit, setSavingVisit] = useState('');
  const [selectionError, setSelectionError] = useState('');
  const points = progress?.points || [];
  const tissues = progress?.tissues || [];
  const ready = points.filter(point => point.status === 'ready');
  const inspected = points.find(point => point.visit_id === inspectedId) || ready.at(-1) || points.at(-1);
  const plotted = positionVisits(points, CHART.left, CHART.width - CHART.left - CHART.right);
  const visible = tissues.filter(tissue => !hidden.includes(tissue.key));
  const comparison = compareTissues(points, tissues);
  const plotBottom = CHART.height - CHART.bottom;
  const y = value => plotBottom - value / 100 * (plotBottom - CHART.top);
  const tickStep = Math.max(1, Math.ceil((points.length - 1) / 5));

  function inspect(point) {
    setInspectedId(point.visit_id);
    onSelectVisit?.(point.visit_id);
  }

  async function chooseImage(point, imageId) {
    setSavingVisit(point.visit_id); setSelectionError('');
    try { await onChooseImage(point.visit_id, imageId); }
    catch (failure) { setSelectionError(failure.message); }
    finally { setSavingVisit(''); }
  }

  return <section className={styles.panel} aria-labelledby={`${chartId}-heading`} aria-busy={loading}>
    <div className={styles.panelHeader}>
      <div>
        <p className={styles.eyebrow}>Wound progress</p>
        <h2 id={`${chartId}-heading`} className={styles.heading}>Tissue trends across visits</h2>
        <p className={styles.subtitle}>Tissue percentage inside the wound mask · {modelLabel || progress?.model_id || 'Selected model'}</p>
      </div>
      <span className={styles.countBadge}>{progress?.summary?.analyzed_visit_count ?? 0} / {progress?.summary?.visit_count ?? 0} visits analyzed</span>
    </div>
    <p className={styles.notice}>Each color represents a tissue type. Percentages describe the selected photo’s wound mask; they are not a healing percentage or a wound size measurement.</p>
    {error ? <div className={styles.trendAlert} role="alert"><p>{error}</p><button type="button" onClick={onRetry}>Retry loading trends</button></div> :
      loading ? <div className={styles.chartEmpty} role="status"><p>Loading tissue trends…</p></div> :
      !points.length ? <div className={styles.emptyState}><h3>Start this wound’s timeline</h3><p>Record a visit and run wound and tissue segmentation. Each visit’s tissue proportions will appear here.</p></div> : <>
        {!!ready.length && <>
          <div className={styles.tissueLegend} aria-label="Visible tissue lines">
            {tissues.map(tissue => <button key={tissue.key} type="button" aria-pressed={!hidden.includes(tissue.key)} onClick={() => setHidden(current => current.includes(tissue.key) ? current.filter(key => key !== tissue.key) : [...current, tissue.key])}>
              <span style={{ background: tissue.color }} aria-hidden="true" />{tissue.label}
            </button>)}
          </div>
          <div className={styles.chartWrap}>
            <svg className={styles.trendChart} viewBox={`0 0 ${CHART.width} ${CHART.height}`} role="img" aria-labelledby={`${chartId}-title ${chartId}-description`}>
              <title id={`${chartId}-title`}>Tissue proportions by visit date</title>
              <desc id={`${chartId}-description`}>Vertical axis: percentage from 0 to 100. Horizontal axis: clinic visit date. Lines stop at visits without comparable results. Exact values and photo choices are in the visit table below.</desc>
              {[0, 25, 50, 75, 100].map(value => <g key={value}><line className={styles.gridLine} x1={CHART.left} x2={CHART.width - CHART.right} y1={y(value)} y2={y(value)} /><text className={styles.axisText} x={CHART.left - 10} y={y(value) + 4} textAnchor="end">{value}%</text></g>)}
              {plotted.map((point, index) => <g key={point.visit_id}>
                {point.visit_id === inspected?.visit_id && <line className={styles.trendCursor} x1={point.x} x2={point.x} y1={CHART.top} y2={plotBottom} />}
                {(index % tickStep === 0 || index === plotted.length - 1) && <text className={styles.axisText} x={point.x} y={plotBottom + 25} textAnchor={index === 0 && points.length > 1 ? 'start' : index === points.length - 1 && points.length > 1 ? 'end' : 'middle'}>{dateLabel(point.visit_date)}</text>}
                {point.status !== 'ready' && <g><line x1={point.x - 4} x2={point.x + 4} y1={plotBottom - 4} y2={plotBottom + 4} stroke="#91a1aa" /><line x1={point.x - 4} x2={point.x + 4} y1={plotBottom + 4} y2={plotBottom - 4} stroke="#91a1aa" /><title>{`${dateLabel(point.visit_date)}: ${point.reason || 'No comparable result'}`}</title></g>}
              </g>)}
              {visible.map(tissue => <g key={tissue.key}>
                {tissueSegments(plotted, tissue.key).map((segment, index) => <g key={index}>
                  {segment.length > 1 && <polyline points={segment.map(point => `${point.x},${y(point.value)}`).join(' ')} fill="none" stroke={tissue.color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" strokeDasharray={tissue.key === 'unclassified' ? '6 4' : undefined} />}
                  {segment.map(point => <circle key={point.visit_id} cx={point.x} cy={y(point.value)} r={point.visit_id === inspected?.visit_id ? 4.5 : 3.5} fill={tissue.color} stroke="white" strokeWidth="1.5" onPointerEnter={() => setInspectedId(point.visit_id)}><title>{`${dateLabel(point.visit_date)} · ${tissue.label}: ${percent(point.value)}`}</title></circle>)}
                </g>)}
              </g>)}
              <text className={styles.axisText} x={(CHART.left + CHART.width - CHART.right) / 2} y={CHART.height - 5} textAnchor="middle">Visit date</text>
            </svg>
          </div>
          {!visible.length && <p className={styles.chartNote}>Select a tissue in the legend to show its line.</p>}
          <p className={styles.chartNote}>{ready.length === 1 ? 'One analyzed visit is shown as points. Analyze another visit to draw the trend lines. ' : ''}Missing results create gaps. Fibrin is unavailable in these trained models. “Unclassified” is tissue background inside the wound mask.</p>
        </>}
        {!ready.length && <div className={styles.chartEmpty}><p>No comparable tissue results yet. Run both segmentation stages for a visit’s selected photo using the model above.</p></div>}
        {inspected && <div className={styles.trendInspection}>
          <label>Inspect visit<select value={inspected.visit_id} onChange={event => inspect(points.find(point => point.visit_id === event.target.value))}>{points.map(point => <option key={point.visit_id} value={point.visit_id}>{dateLabel(point.visit_date)}</option>)}</select></label>
          <div className={styles.trendValues}>{inspected.status === 'ready' ? tissues.map(tissue => <span key={tissue.key}><i style={{ background: tissue.color }} aria-hidden="true" />{tissue.label}<strong>{percent(inspected.percentages[tissue.key])}</strong></span>) : <p>{inspected.reason || 'This visit has no comparable tissue result.'}</p>}</div>
        </div>}
        <div className={styles.trendComparison}>
          <h3>Tissue composition change</h3>
          {comparison ? <><p>{dateLabel(comparison.first.visit_date)} → {dateLabel(comparison.last.visit_date)} · percentage points (pp)</p><div className={styles.trendChangeGrid}>{comparison.changes.map(tissue => <div key={tissue.key}><span><i style={{ background: tissue.color }} aria-hidden="true" />{tissue.label}</span><strong>{delta(tissue.change)}</strong><small>{percent(tissue.before)} → {percent(tissue.after)}</small></div>)}</div>{!!comparison.skippedVisits && <p>{comparison.skippedVisits} intervening {comparison.skippedVisits === 1 ? 'visit has' : 'visits have'} no comparable result.</p>}</> : <p>Analyze at least two visits with the same model to compare tissue proportions.</p>}
          <p>Changes in tissue composition alone do not determine whether the wound is healing. Healing percentage and outcome assessment will follow your chosen method.</p>
        </div>
        {selectionError && <p role="alert" className={styles.trendAlert}>{selectionError}</p>}
        <details className={styles.measurements} open>
          <summary>Visit results and selected photos <span>{points.length}</span></summary>
          <p className={styles.chartNote}>One photo per visit avoids counting the same wound multiple times. The first uploaded photo is selected by default; choose another when needed.</p>
          <div className={styles.tableWrap}><table className={styles.table}>
            <caption className={styles.srOnly}>Exact tissue percentages for each clinic visit. Unavailable values are shown as a dash.</caption>
            <thead><tr><th scope="col">Visit</th><th scope="col">Photo used for trends</th><th scope="col">Result</th>{tissues.map(tissue => <th key={tissue.key} scope="col">{tissue.label}</th>)}</tr></thead>
            <tbody>{points.map(point => <tr key={point.visit_id}>
              <th scope="row"><button type="button" className={styles.trendDateButton} onClick={() => inspect(point)}>{dateLabel(point.visit_date)}</button></th>
              <td>{point.images.length > 1 ? <select aria-label={`Photo used for ${dateLabel(point.visit_date)}`} value={point.image_id || ''} disabled={!!savingVisit || !onChooseImage || loading} onChange={event => chooseImage(point, event.target.value)}>{point.images.map(image => <option key={image.id} value={image.id}>{image.filename}</option>)}</select> : point.images[0]?.filename || 'No image'}{savingVisit === point.visit_id && <small role="status"> Saving…</small>}</td>
              <td><span className={point.status === 'ready' ? styles.trendReady : styles.trendMissing}>{point.status === 'ready' ? 'Analyzed' : point.status === 'no_wound' ? 'No wound detected' : point.status === 'failed' ? 'Analysis failed' : point.status === 'unavailable' ? 'Unavailable' : 'Needs analysis'}</span>{point.reason && <small className={styles.trendReason}>{point.reason}</small>}</td>
              {tissues.map(tissue => <td key={tissue.key}>{percent(point.percentages?.[tissue.key])}</td>)}
            </tr>)}</tbody>
          </table></div>
        </details>
      </>}
  </section>;
}
