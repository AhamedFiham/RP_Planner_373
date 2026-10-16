'use client';
import { ClipboardList, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { percent } from '@/lib/retinopathy/constants';
import { displayHistoricalQuality, normalizeRecord } from '@/lib/retinopathy/contract';
import useRetinopathyArtifacts from '@/hooks/useRetinopathyArtifacts';
import RetinopathyResult from './RetinopathyResult';

function Detail({ id, api }) {
  const [record, setRecord] = useState(null); const [result, setResult] = useState(null); const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    api.detail(id,controller.signal).then(data => { if (!active) return; const view=normalizeRecord(data); setResult(view); setRecord(data); }).catch(e => { if (active) setError(e.status !== undefined ? e.message : 'Saved result could not be read.'); });
    return () => { active=false;controller.abort(); };
  },[api,id]);
  if (error) return <p role="alert" className="retino-error">{error}</p>;
  if (!record) return <p role="status">Loading saved assessment…</p>;
  return <div className="retino-record-details"><p>Status: {record.assessment_status} · Quality: {displayHistoricalQuality(record.image_quality)} · Quality model: {record.quality_model_version || 'Unavailable'}</p><p>Original quality probabilities and guidance text were not retained in this record.</p>{result ? <RetinopathyResult api={api} result={result} /> : <><p>No saved severity prediction. This record is {record.assessment_status.replaceAll('_',' ')}.</p><StoredOriginal record={record} api={api} /></>}</div>;
}
function StoredOriginal({ record, api }) {
  const [reference] = useState(() => ({ original: record.artifacts?.find(a=>a.artifact_type==='original')?.url }));
  const images=useRetinopathyArtifacts(api,reference);
  return <>{images.loading && <p role="status">Loading original image…</p>}{images.error && <p role="alert">{images.error}</p>}{images.urls[reference.original] && <img className="retino-attention-image" src={images.urls[reference.original]} alt="Stored original retinal image" />}</>;
}
export default function RetinopathyHistory({ api, revision, onDeleted }) {
  const [page,setPage]=useState(1);const [refresh,setRefresh]=useState(0);const [data,setData]=useState(null);const [error,setError]=useState('');const [open,setOpen]=useState(null);const [confirm,setConfirm]=useState(null);const [deleting,setDeleting]=useState(false);
  useEffect(()=> {
    const controller=new AbortController(); let active=true;setData(null);setError('');setOpen(null);
    api.history(page,controller.signal).then(value=>{if(active)setData(value);}).catch(e=>{if(active)setError(e.message);});
    return ()=>{active=false;controller.abort();};
  },[api,page,refresh,revision]);
  // Deletion requests are cancelled on unmount; refresh resolves any uncertain outcome.
  useEffect(()=>{if(!deleting || !confirm)return;const controller=new AbortController();let active=true;
    api.remove(confirm,controller.signal).then(()=>{if(active){onDeleted?.(confirm);setConfirm(null);setOpen(null);setRefresh(v=>v+1);}}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setDeleting(false);});
    return ()=>{active=false;controller.abort();};
  },[api,deleting,confirm]);
  return <section className="retino-card" aria-labelledby="history-title">
    <div className="retino-card-heading"><div className="retino-icon blue"><ClipboardList size={20} /></div><div><h2 id="history-title">Recent Retinopathy Assessments</h2><p>Your saved assessment history, newest first.</p></div></div>
    {error && <p className="retino-error" role="alert">{error}</p>}{!data && !error && <p role="status">Loading history…</p>}{data?.items.length===0 && <p>No assessments on this page.</p>}
    <div className="retino-history-table-wrap" tabIndex={0} role="region" aria-label="Assessment history"><table className="retino-history-table"><thead><tr><th>Assessment date</th><th>Severity / status</th><th>Confidence</th><th>Image quality</th><th>Actions</th></tr></thead><tbody>{data?.items.map(record=><tr key={record.id}><th scope="row">{new Date(record.created_at).toLocaleString()}</th><td>{record.severity_label || 'No prediction'} · {record.assessment_status}</td><td>{record.confidence == null ? 'Unavailable' : `${percent(record.confidence)} (${record.is_calibrated ? 'calibrated' : 'uncalibrated'})`}</td><td>{displayHistoricalQuality(record.image_quality)}</td><td><div className="retino-history-actions"><button className="retino-details-button" type="button" onClick={()=>setOpen(open===record.id?null:record.id)} aria-expanded={open===record.id}>View details</button><button className="retino-details-button retino-delete-button" type="button" disabled={deleting} onClick={()=>setConfirm(record.id)} aria-label={`Delete assessment from ${new Date(record.created_at).toLocaleString()}`}><Trash2 size={14} aria-hidden="true" />Delete</button></div></td></tr>)}</tbody></table></div>
    {confirm && <div className="retino-record-details" role="group" aria-label="Confirm assessment deletion"><p>Delete this assessment and its stored retinal images? This cannot be undone.</p><button className="retino-button ghost" disabled={deleting} onClick={()=>setDeleting(true)}>{deleting?'Deleting…':'Confirm deletion'}</button><button className="retino-button ghost" disabled={deleting} onClick={()=>setConfirm(null)}>Cancel</button></div>}
    {open && <Detail key={open} id={open} api={api} />}
    <div className="retino-upload-actions"><button className="retino-button ghost" disabled={page===1} onClick={()=>setPage(p=>p-1)}>Previous</button><span>Page {page}{data?` · ${data.total} assessments`:''}</span><button className="retino-button ghost" disabled={!data || page*data.limit>=data.total} onClick={()=>setPage(p=>p+1)}>Next</button><button className="retino-button ghost" onClick={()=>setRefresh(v=>v+1)}>Refresh history</button></div>
  </section>;
}
