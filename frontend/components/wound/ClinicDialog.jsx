'use client';

import { useEffect, useRef, useState } from 'react';
import { UploadCloud, X } from 'lucide-react';
import styles from './clinic.module.css';

function today() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export default function ClinicDialog({ kind, patient, wound, onSave, onClose }) {
  const dialog = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const title = { patient: 'Create a patient', wound: 'Assign a wound', visit: 'Record a visit' }[kind];

  useEffect(() => {
    const element = dialog.current;
    if (!element.open) element.showModal();
    return () => { if (element.open) element.close(); };
  }, []);
  useEffect(() => {
    const items = files.map(file => ({ name: file.name, url: URL.createObjectURL(file) }));
    setPreviews(items);
    return () => items.forEach(item => URL.revokeObjectURL(item.url));
  }, [files]);

  function chooseFiles(event) {
    const items = Array.from(event.target.files || []);
    const invalid = items.length > 5 ? 'Choose up to five images for this visit.' :
      items.some(file => !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) ? 'Choose JPEG, PNG, or WebP images.' :
      items.some(file => file.size > 10 * 1024 * 1024 || file.size === 0) ? 'Each image must be nonempty and no larger than 10 MB.' : '';
    setError(invalid); setFiles(invalid ? [] : items);
    if (invalid) event.target.value = '';
  }
  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    const form = new FormData(event.currentTarget);
    let body;
    if (kind === 'visit') {
      if (!files.length) { setError('Choose at least one wound image.'); return; }
      body = new FormData();
      body.append('visit_date', form.get('visit_date'));
      body.append('notes', form.get('notes') || '');
      files.forEach(file => body.append('images', file));
    } else {
      body = Object.fromEntries(form);
      if (kind === 'wound' && !body.onset_date) delete body.onset_date;
    }
    setBusy(true); setError('');
    try { await onSave(body); onClose(); }
    catch (error) { setError(error.message); }
    finally { setBusy(false); }
  }

  return <dialog ref={dialog} className={styles.dialog} aria-labelledby="clinic-dialog-title" onCancel={event => { event.preventDefault(); if (!busy) onClose(); }}>
    <form onSubmit={submit}>
      <header className={styles.dialogHeader}><div><p className={styles.eyebrow}>WOUND CLINIC</p><h2 id="clinic-dialog-title">{title}</h2></div><button type="button" className={styles.iconButton} aria-label="Close form" onClick={onClose} disabled={busy}><X size={20} /></button></header>
      {kind !== 'patient' && <p className={styles.formContext}>{patient.patient_code} · {patient.display_name}{kind === 'visit' ? ` / ${wound.label}` : ''}</p>}
      <fieldset disabled={busy} className={styles.fields}>
        {kind === 'patient' && <>
          <label htmlFor="patient-code">Patient ID<input autoFocus id="patient-code" name="patient_code" minLength={2} maxLength={40} placeholder="e.g. PT-001" autoComplete="off" required /></label>
          <label htmlFor="patient-name">Patient name<input id="patient-name" name="display_name" minLength={2} maxLength={100} autoComplete="off" placeholder="Full name" required /></label>
          <p className={styles.help}>Use a unique clinic ID. Each patient’s wounds and visit images are kept separately.</p>
        </>}
        {kind === 'wound' && <>
          <label htmlFor="wound-label">Wound label<input autoFocus id="wound-label" name="label" minLength={2} maxLength={100} placeholder="e.g. Left heel ulcer" required /></label>
          <label htmlFor="wound-location">Anatomical location<input id="wound-location" name="location" minLength={2} maxLength={100} placeholder="e.g. Left foot, heel" required /></label>
          <label htmlFor="wound-onset">Onset date <span>(optional)</span><input id="wound-onset" name="onset_date" type="date" max={today()} /></label>
          <p className={styles.help}>A wound ID is assigned automatically. Visits and analysis belong to this wound only.</p>
        </>}
        {kind === 'visit' && <>
          <label htmlFor="visit-date">Visit date<input autoFocus id="visit-date" name="visit_date" type="date" defaultValue={today()} max={today()} required /></label>
          <label htmlFor="visit-images" className={styles.uploadLabel}><UploadCloud size={25} /><strong>Choose wound photographs</strong><span>Up to 5 JPEG, PNG, or WebP images · 10 MB each</span><input id="visit-images" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={chooseFiles} required /></label>
          {!!previews.length && <div className={styles.previews}>{previews.map((file, index) => <figure key={`${file.name}-${index}`}><img src={file.url} alt={`Selected photograph ${index + 1}`} /><figcaption>{file.name}</figcaption></figure>)}</div>}
          <p className={styles.help}>Record the date the images were captured. Analysis will remain pending until the models are connected.</p>
        </>}
        <label htmlFor="record-notes">{kind === 'visit' ? 'Visit notes' : 'Notes'} <span>(optional)</span><textarea id="record-notes" name="notes" maxLength={2000} rows={3} placeholder={kind === 'visit' ? 'Observations recorded at this visit…' : 'Additional clinic notes…'} /></label>
      </fieldset>
      {error && <p className={styles.formError} role="alert">{error}</p>}
      <footer className={styles.dialogFooter}><button type="button" className={styles.secondaryButton} onClick={onClose} disabled={busy}>Cancel</button><button type="submit" className={styles.primaryButton} disabled={busy}>{busy ? 'Saving…' : { patient: 'Create patient', wound: 'Create wound', visit: 'Save visit images' }[kind]}</button></footer>
    </form>
  </dialog>;
}
