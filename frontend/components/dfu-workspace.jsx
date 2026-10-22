'use client';

import { useEffect, useState } from 'react';
import { ArrowRight, CalendarDays, Check, ChevronRight, ClipboardList, ImagePlus, Plus, Search, ShieldCheck, Users, X } from 'lucide-react';
import { useAuth } from '@/components/auth-provider';
import DashboardShell from '@/components/dashboard/DashboardShell';
import useWoundClinic from '@/hooks/useWoundClinic';
import useVisitComparison from '@/hooks/useVisitComparison';
import ClinicDialog from '@/components/wound/ClinicDialog';
import PrivateImage from '@/components/wound/PrivateImage';
import HealingChart from '@/components/wound/HealingChart';
import ModelAnalysisPanel from '@/components/wound/ModelAnalysisPanel';
import TissueComparison from '@/components/wound/TissueComparison';
import { woundRequest } from '@/lib/wound-api';
import styles from '@/components/wound/clinic.module.css';

function displayDate(value) {
  if (!value) return '—';
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}
function shortId(value) { return `WND-${value.slice(0, 8).toUpperCase()}`; }
const modelLabels = { unet_resnet18: 'U-Net · ResNet18', deeplabv3plus_mobilenet_v2: 'DeepLabV3+ · MobileNet V2', segformer_mit_b0: 'SegFormer · MiT-B0' };

export default function DfuWorkspace() {
  const { token, ready } = useAuth() || {};
  const [modelId, setModelId] = useState('');
  const [modelCatalog, setModelCatalog] = useState(null);
  const clinic = useWoundClinic(token, modelId);
  const [search, setSearch] = useState('');
  const [dialog, setDialog] = useState('');
  const [tab, setTab] = useState('overview');
  const [visitId, setVisitId] = useState('');
  const [statusBusy, setStatusBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const { patient, wound, visits, progress } = clinic;
  const visitRecord = visits.find(visit => visit.id === visitId) || visits.at(-1);
  const selectedVisit = visitRecord ? { ...visitRecord, progress_image_id: progress?.points.find(point => point.visit_id === visitRecord.id)?.image_id || visitRecord.progress_image_id } : undefined;
  const comparison = useVisitComparison({ token, woundId: wound?.id, modelId, progress, onComplete: clinic.refreshProgress });
  const modelChoices = modelCatalog?.token === token ? modelCatalog.models : [];
  const filteredPatients = clinic.patients.filter(item => `${item.patient_code} ${item.display_name}`.toLowerCase().includes(search.toLowerCase()));

  useEffect(() => {
    if (!token) { setModelCatalog(null); setModelId(''); return; }
    const controller = new AbortController();
    woundRequest('/models', token, { signal: controller.signal }).then(data => {
      if (controller.signal.aborted) return;
      setModelCatalog({ token, models: data.models });
      setModelId(current => data.models.some(model => model.id === current) ? current : data.selected_model_id || '');
    }).catch(() => { /* The analysis and progress panels display actionable API errors. */ });
    return () => controller.abort();
  }, [token]);

  async function saveRecord(body) {
    if (dialog === 'patient') await clinic.createPatient(body);
    if (dialog === 'wound') await clinic.createWound(body);
    if (dialog === 'visit') { const visit = await clinic.createVisit(body); setVisitId(visit.id); setTab('visits'); }
    setNotice({ patient: 'Patient created. You can now assign a wound.', wound: 'Wound created. You can now record the first visit.', visit: 'Visit images saved. Model analysis is pending.' }[dialog]);
  }
  async function toggleWoundStatus() {
    setStatusBusy(true); setActionError('');
    try { await clinic.changeStatus(wound.status === 'healed' ? 'active' : 'healed'); setNotice(wound.status === 'healed' ? 'Wound reopened.' : 'Wound marked as healed. Its visit history is preserved.'); }
    catch (error) { setActionError(error.message); }
    finally { setStatusBusy(false); }
  }

  return <DashboardShell title="Wound Clinic">
    <div className={styles.workspace}>
      <header className={styles.heading}>
        <div><p className={styles.eyebrow}>CLINIC WORKSPACE</p><h2>Every patient. Every wound. Every visit.</h2><p>A continuous image record, from the first visit to follow-up.</p></div>
        <button type="button" className={styles.primaryButton} onClick={() => setDialog('patient')} disabled={!token}><Plus size={16} /> New patient</button>
      </header>
      <ol className={styles.steps} aria-label="Clinic workflow">
        <li className={patient ? styles.completed : styles.current}><span>{patient ? <Check size={14} /> : '1'}</span> Select patient</li><li aria-hidden="true"><ChevronRight size={15} /></li>
        <li className={wound ? styles.completed : patient ? styles.current : ''}><span>{wound ? <Check size={14} /> : '2'}</span> Assign wound</li><li aria-hidden="true"><ChevronRight size={15} /></li>
        <li className={visits.length ? styles.completed : wound ? styles.current : ''}><span>{visits.length ? <Check size={14} /> : '3'}</span> Record visits</li><li aria-hidden="true"><ChevronRight size={15} /></li>
        <li><span>4</span> Review analysis <small>Tissue trends</small></li>
      </ol>
      {(clinic.error || actionError) && <div className={styles.errorBanner} role="alert"><span>{clinic.error || actionError}</span><button type="button" onClick={() => { setActionError(''); clinic.refresh(); }}>Try again</button></div>}
      {notice && <div className={styles.notice} role="status"><Check size={16} /><span>{notice}</span><button type="button" onClick={() => setNotice('')} aria-label="Dismiss notification"><X size={16} /></button></div>}
      {!ready || !token ? <div className={styles.empty}><ShieldCheck size={30} /><h3>Opening your clinic workspace</h3><p>A signed-in session is required to access patient records.</p></div> :
      <div className={styles.layout}>
        <aside className={styles.patientPanel} aria-label="Patient records">
          <div className={styles.panelHeading}><div><Users size={18} /><h3>Patients</h3><span className={styles.count}>{clinic.patients.length}</span></div></div>
          <label className={styles.search}><Search size={16} /><input aria-label="Search patients by ID or name" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search ID or name" /></label>
          <div className={styles.patientList} aria-busy={clinic.loading.patients}>
            {clinic.loading.patients && !clinic.patients.length ? <p className={styles.listEmpty}>Loading patients…</p> : !filteredPatients.length ? <div className={styles.listEmpty}><p>{clinic.patients.length ? 'No matching patients.' : 'Your patient list starts here.'}</p>{!clinic.patients.length && <button className={styles.textButton} type="button" onClick={() => setDialog('patient')}>Create your first patient <ArrowRight size={14} /></button>}</div> :
            filteredPatients.map(item => <button type="button" key={item.id} className={`${styles.patientItem} ${clinic.patientId === item.id ? styles.patientSelected : ''}`} onClick={() => { clinic.selectPatient(item.id); setNotice(''); setActionError(''); setVisitId(''); }} aria-pressed={clinic.patientId === item.id}>
              <span className={styles.patientAvatar}>{item.display_name.slice(0, 1).toUpperCase()}</span><span><small>{item.patient_code}</small><strong>{item.display_name}</strong><em>{item.wound_count || 0} {(item.wound_count || 0) === 1 ? 'wound' : 'wounds'}</em></span><ChevronRight size={15} />
            </button>)}
          </div>
          <p className={styles.panelFootnote}>Each patient has a separate wound and visit history.</p>
        </aside>
        <div className={styles.content}>
          {!patient ? <section className={styles.empty}><Users size={34} /><h3>{clinic.loading.patients ? 'Loading clinic records…' : 'Create a patient to begin'}</h3><p>Register a patient, assign their wound, then add images for each clinic visit.</p>{!clinic.loading.patients && <button className={styles.primaryButton} onClick={() => setDialog('patient')} type="button"><Plus size={16} /> Create patient</button>}</section> : <>
            <section className={styles.patientHeader}>
              <div><p className={styles.eyebrow}>{patient.patient_code}</p><h2>{patient.display_name}</h2>{patient.notes && <p className={styles.recordNotes}>{patient.notes}</p>}</div>
              <button type="button" className={styles.secondaryButton} onClick={() => setDialog('wound')}><Plus size={16} /> Assign wound</button>
            </section>
            <section className={styles.woundBar} aria-busy={clinic.loading.wounds}>
              <label htmlFor="clinic-wound">Wound record<select id="clinic-wound" value={clinic.woundId} onChange={event => { clinic.selectWound(event.target.value); setVisitId(''); setActionError(''); }} disabled={!clinic.wounds.length || clinic.loading.wounds}>
                {!clinic.wounds.length && <option value="">{clinic.loading.wounds ? 'Loading wounds…' : 'No wounds assigned'}</option>}
                {clinic.wounds.map(item => <option key={item.id} value={item.id}>{item.label} · {shortId(item.id)}{item.status === 'healed' ? ' · Healed' : ''}</option>)}
              </select></label>
              {wound && <><div className={styles.woundLocation}><span>Location</span><strong>{wound.location}</strong></div><span className={`${styles.status} ${wound.status === 'healed' ? styles.healed : ''}`}>{wound.status === 'healed' ? 'Healed' : 'Active wound'}</span></>}
            </section>
            {!wound ? <section className={styles.empty}><ClipboardList size={34} /><h3>{clinic.loading.wounds ? 'Loading wound records…' : 'Assign this patient’s first wound'}</h3><p>A separate wound ID keeps photographs and analysis together, even when a patient has multiple wounds.</p>{!clinic.loading.wounds && <button type="button" className={styles.primaryButton} onClick={() => setDialog('wound')}><Plus size={16} /> Assign wound</button>}</section> : <>
              <div className={styles.recordToolbar}><div className={styles.tabs} aria-label="Wound record views"><button type="button" aria-pressed={tab === 'overview'} className={tab === 'overview' ? styles.tabActive : ''} onClick={() => setTab('overview')}>Overview</button><button type="button" aria-pressed={tab === 'visits'} className={tab === 'visits' ? styles.tabActive : ''} onClick={() => setTab('visits')}>Visit history <span>{visits.length}</span></button><button type="button" aria-pressed={tab === 'comparison'} className={tab === 'comparison' ? styles.tabActive : ''} onClick={() => setTab('comparison')}>Tissue comparison</button></div><button type="button" className={styles.primaryButton} onClick={() => setDialog('visit')} disabled={wound.status === 'healed' || clinic.loading.visits}><ImagePlus size={16} /> Record visit</button></div>
              <div className={styles.stats}><div><span>Recorded visits</span><strong>{visits.length}</strong></div><div><span>Latest visit</span><strong>{displayDate(visits.at(-1)?.visit_date)}</strong></div><div><span>Tissue trends</span><strong>{clinic.progressLoading ? 'Loading…' : `${progress?.summary?.analyzed_visit_count ?? 0} analyzed visits`}</strong></div></div>
              {wound.status === 'healed' && <p className={styles.infoNote}>This wound is marked as healed. Its images remain available; reopen it to record another visit.</p>}
              {clinic.loading.visits ? <section className={styles.empty} role="status"><p>Loading visit images and progress…</p></section> : tab === 'overview' ? <div className={styles.overview}>
                <ModelAnalysisPanel key={wound.id} visit={selectedVisit} visits={visits} onSelectVisit={setVisitId} token={token} selectedModelId={modelId} onModelChange={setModelId} onAnalysisComplete={clinic.refreshProgress} progress={progress} progressLoading={clinic.progressLoading} progressError={clinic.progressError} onCompareVisits={() => setTab('comparison')} onRefreshProgress={clinic.refreshProgress} onModelsLoaded={data => setModelCatalog({ token, models: data.models })} />
                <HealingChart key={`${wound.id}:${modelId}`} progress={progress} loading={clinic.progressLoading} error={clinic.progressError} modelLabel={modelLabels[modelId]} onRetry={clinic.refreshProgress} onChooseImage={clinic.selectProgressImage} onSelectVisit={setVisitId} />
              </div> : tab === 'comparison' ? <div className={styles.overview}>
                <div className={styles.comparisonToolbar}>
                  <label>Segmentation model<select value={modelId} onChange={event => setModelId(event.target.value)} disabled={!modelChoices.length || comparison.analyzing}>
                    {!modelChoices.length && <option value={modelId}>{modelLabels[modelId] || 'Select a model in Overview'}</option>}
                    {modelChoices.map(model => <option key={model.id} value={model.id}>{model.label}</option>)}
                  </select></label>
                  <button type="button" className={styles.secondaryButton} onClick={clinic.refreshProgress} disabled={comparison.analyzing || clinic.progressLoading}>Refresh results</button>
                </div>
                <TissueComparison key={`${wound.id}:${modelId}`} progress={progress} loading={clinic.progressLoading} error={clinic.progressError} onRetry={clinic.refreshProgress} token={token} onChooseImage={clinic.selectProgressImage} onAnalyze={comparison.analyzeVisits} analyzing={comparison.analyzing} analysisMessage={comparison.analysisMessage} onInspectVisit={id => { setVisitId(id); setTab('overview'); }} />
                <HealingChart key={`comparison-chart:${wound.id}:${modelId}`} progress={progress} loading={clinic.progressLoading} error={clinic.progressError} modelLabel={modelLabels[modelId]} onRetry={clinic.refreshProgress} onChooseImage={comparison.analyzing ? undefined : clinic.selectProgressImage} onSelectVisit={setVisitId} />
              </div> : <section className={styles.visitSection}>
                <div className={styles.sectionHeading}><div><h3>Visit image history</h3><p>Wound images ordered by capture date.</p></div><CalendarDays size={21} /></div>
                {!visits.length ? <div className={styles.empty}><ImagePlus size={32} /><h3>Record the first visit</h3><p>Add the visit date and wound images to start this wound’s visit history.</p><button type="button" className={styles.secondaryButton} onClick={() => setDialog('visit')} disabled={wound.status === 'healed'}>Add visit images</button></div> : <div className={styles.visitLayout}>
                  <ol className={styles.visitList}>{visits.map((visit, index) => <li key={visit.id}><button type="button" className={`${styles.visitItem} ${visit.id === selectedVisit?.id ? styles.visitSelected : ''}`} aria-pressed={visit.id === selectedVisit?.id} onClick={() => setVisitId(visit.id)}><span className={styles.visitMarker}>{index + 1}</span><span><strong>{displayDate(visit.visit_date)}</strong><small>{index === 0 ? 'First visit' : `Follow-up ${index}`} · {visit.images.length} {visit.images.length === 1 ? 'image' : 'images'}</small></span><ChevronRight size={14} /></button></li>)}</ol>
                  {selectedVisit && <article className={styles.visitDetail}><div className={styles.imageHeading}><h4>{displayDate(selectedVisit.visit_date)}</h4><span className={styles.pending}>Original images</span></div><div className={styles.visitImages}>{selectedVisit.images.map((image, index) => <figure key={image.id}><PrivateImage image={image} token={token} className={styles.visitImage} alt={`Wound photograph ${index + 1}, ${displayDate(selectedVisit.visit_date)}`} /><figcaption>{image.filename}</figcaption></figure>)}</div>{selectedVisit.notes && <div className={styles.visitNotes}><strong>Visit notes</strong><p>{selectedVisit.notes}</p></div>}</article>}
                </div>}
              </section>}
              <footer className={styles.woundFooter}><span>{shortId(wound.id)}{wound.onset_date ? ` · Onset ${displayDate(wound.onset_date)}` : ''}{wound.notes && <span className={styles.woundNotes}>{wound.notes}</span>}</span><button type="button" className={styles.textButton} onClick={toggleWoundStatus} disabled={statusBusy}>{statusBusy ? 'Updating…' : wound.status === 'healed' ? 'Reopen wound' : 'Mark wound as healed'}</button></footer>
            </>}
          </>}
        </div>
      </div>}
      {dialog && <ClinicDialog key={dialog} kind={dialog} patient={patient} wound={wound} onSave={saveRecord} onClose={() => setDialog('')} />}
    </div>
  </DashboardShell>;
}
