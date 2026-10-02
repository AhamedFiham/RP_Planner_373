'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

const acceptedTypes = ['image/jpeg', 'image/png', 'image/webp'];
const maxImageBytes = 10 * 1024 * 1024;

function ImagePlaceholderIcon() {
  return (
    <svg viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
      <rect x="6" y="9" width="52" height="46" rx="8" stroke="currentColor" strokeWidth="2" />
      <circle cx="22" cy="23" r="5" fill="currentColor" />
      <path d="m13 47 14-15 9 9 6-6 10 12H13Z" fill="currentColor" />
    </svg>
  );
}

function displayDate(date) {
  const [year, month, day] = date.split('-');
  return `${day}/${month}/${year}`;
}

export default function DfuWorkspace() {
  const [caseId, setCaseId] = useState('');
  const [selected, setSelected] = useState(null);
  const [visits, setVisits] = useState([]);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const dateInputRef = useRef(null);
  const imageUrls = useRef(new Set());

  useEffect(() => {
    const urls = imageUrls.current;
    return () => {
      for (const url of urls) URL.revokeObjectURL(url);
      urls.clear();
    };
  }, []);

  function releaseUrl(url) {
    if (!url) return;
    URL.revokeObjectURL(url);
    imageUrls.current.delete(url);
  }

  function clearSelection() {
    releaseUrl(selected?.url);
    setSelected(null);
    if (inputRef.current) inputRef.current.value = '';
  }

  function handleImageChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    clearSelection();
    setError('');

    if (!acceptedTypes.includes(file.type)) {
      setError('Choose a JPEG, PNG, or WebP image.');
      return;
    }
    if (file.size > maxImageBytes) {
      setError('Choose an image smaller than 10 MB.');
      return;
    }

    const url = URL.createObjectURL(file);
    imageUrls.current.add(url);
    setSelected({ name: file.name, url });
  }

  function addVisit(event) {
    event.preventDefault();
    const researchId = caseId.trim();
    const visitDate = dateInputRef.current?.value ?? '';

    if (!researchId || !visitDate || !selected) {
      setError('Enter a research case ID, visit date, and image before adding the visit.');
      return;
    }
    if (visits.some(visit => visit.date === visitDate)) {
      setError('This case already has an image for that visit date. Choose a different date or remove the earlier entry.');
      return;
    }

    const newVisit = { date: visitDate, name: selected.name, url: selected.url };
    setVisits(current => [...current, newVisit].sort((a, b) => a.date.localeCompare(b.date)));
    setCaseId(researchId);
    setSelected(null);
    if (dateInputRef.current) dateInputRef.current.value = '';
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  }

  function removeVisit(date) {
    const visit = visits.find(item => item.date === date);
    releaseUrl(visit?.url);
    setVisits(current => current.filter(item => item.date !== date));
  }

  function clearCase() {
    if (!window.confirm('Discard this case and its visit images from this browser tab?')) return;
    clearSelection();
    for (const visit of visits) releaseUrl(visit.url);
    setVisits([]);
    setCaseId('');
    if (dateInputRef.current) dateInputRef.current.value = '';
    setError('');
  }

  const currentImage = selected ?? visits.at(-1) ?? null;

  return (
    <div className="dfu-page">
      <div className="dfu-page-inner">
        <header className="dfu-heading">
          <Link className="dfu-back" href="/home">← Back to home</Link>
          <p className="dfu-kicker">DFU / Wound healing research</p>
          <h1>See the journey, visit by visit.</h1>
          <p>Collect dated wound images here. Future image analysis will support a conditional healing estimate and changes between visits.</p>
        </header>

        <div className="dfu-workspace-grid">
          <div className="dfu-left-column">
            <section className="dfu-card dfu-upload-card" aria-labelledby="dfu-upload-title">
              <div className="dfu-card-heading">
                <span className="dfu-step">01</span>
                <div>
                  <h2 id="dfu-upload-title">Upload a visit image</h2>
                  <p>Use a research case ID and the actual date the image was taken.</p>
                </div>
              </div>

              <form onSubmit={addVisit} noValidate>
                <label htmlFor="dfu-case-id">Research case ID</label>
                <input
                  id="dfu-case-id"
                  type="text"
                  value={caseId}
                  onChange={event => setCaseId(event.target.value)}
                  disabled={visits.length > 0}
                  maxLength={40}
                  autoComplete="off"
                  placeholder="e.g. DFU-001"
                  required
                />
                <p className="dfu-field-help">Use a study code, not a patient name. The ID stays fixed after the first visit.</p>

                <label htmlFor="dfu-visit-date">Visit date</label>
                <input
                  id="dfu-visit-date"
                  ref={dateInputRef}
                  type="date"
                  required
                />

                <label htmlFor="dfu-image">Wound photograph</label>
                <input
                  id="dfu-image"
                  ref={inputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleImageChange}
                  aria-describedby="dfu-image-help"
                  required
                />
                <p className="dfu-field-help" id="dfu-image-help">JPEG, PNG, or WebP · Up to 10 MB</p>

                {error && <p className="dfu-form-error" role="alert">{error}</p>}

                <div className="dfu-form-actions">
                  <button className="dfu-primary-button" type="submit">Add visit image <span aria-hidden="true">↗</span></button>
                  {selected && <button className="dfu-text-button" type="button" onClick={clearSelection}>Remove selection</button>}
                </div>
              </form>
            </section>

            <section className="dfu-card dfu-image-card" aria-labelledby="dfu-image-title">
              <div className="dfu-card-heading compact">
                <span className="dfu-step">02</span>
                <div>
                  <h2 id="dfu-image-title">Visit image</h2>
                  <p>{selected ? 'Selected image, ready to add' : visits.length ? `Latest visit · ${displayDate(visits.at(-1).date)}` : 'Your uploaded image will appear here'}</p>
                </div>
              </div>
              <div className="dfu-image-frame">
                {currentImage ? <img src={currentImage.url} alt="Selected diabetic foot ulcer visit" /> : <ImagePlaceholderIcon />}
              </div>
              {currentImage && <p className="dfu-image-filename">{currentImage.name}</p>}
            </section>

            <section className="dfu-card dfu-image-card" aria-labelledby="dfu-area-title">
              <div className="dfu-card-heading compact">
                <span className="dfu-step">03</span>
                <div>
                  <h2 id="dfu-area-title">Classified wound area</h2>
                  <p>Future model output</p>
                </div>
              </div>
              <div className="dfu-image-frame dfu-classified-placeholder">
                <ImagePlaceholderIcon />
                <span>Area analysis will appear here</span>
              </div>
              <p className="dfu-muted-note">No wound boundary or area has been calculated.</p>
            </section>
          </div>

          <div className="dfu-right-column">
            <section className="dfu-card dfu-outlook-card" aria-labelledby="dfu-outlook-title">
              <div className="dfu-card-heading">
                <span className="dfu-step">04</span>
                <div>
                  <h2 id="dfu-outlook-title">Healing outlook</h2>
                  <p>Explanation and estimated timing</p>
                </div>
              </div>
              <div className="dfu-status"><span aria-hidden="true" /> Awaiting model analysis</div>
              <p className="dfu-outlook-copy">
                {visits.length
                  ? 'The visit image is ready. A healing estimate will appear when a validated prediction model is connected.'
                  : 'Add a dated visit image to begin. This prototype does not calculate a healing prediction yet.'}
              </p>
              <div className="dfu-outlook-metrics">
                <div><span>Estimated healing date</span><strong>—</strong></div>
                <div><span>Possible date range</span><strong>—</strong></div>
              </div>
              <div className="dfu-explanation">
                <strong>Wound analysis</strong>
                <p>Image-derived wound findings and an explanation will appear here after the classifier is connected.</p>
              </div>
              <div className="dfu-guidance-note">
                <strong>Care guidance</strong>
                <p>A clinician-approved care plan will appear here when available. A future healing date could be conditional on following that plan, but it would remain an estimate, not a guarantee or a substitute for clinical review.</p>
              </div>
            </section>

            <section className="dfu-card dfu-progress-card" aria-labelledby="dfu-progress-title">
              <div className="dfu-card-heading">
                <span className="dfu-step">05</span>
                <div>
                  <h2 id="dfu-progress-title">Progress across visits</h2>
                  <p>Compare each image with the previous dated visit</p>
                </div>
              </div>
              <div className="dfu-chart" role="img" aria-label="No wound area change percentages are available yet">
                <div className="dfu-chart-empty-bars" aria-hidden="true"><span /><span /><span /></div>
                <div className="dfu-chart-axis" aria-hidden="true" />
                <p>Wound-area change graph will appear after image analysis.</p>
              </div>
              <p className="dfu-muted-note">The first image is the baseline. A percentage can only compare a later visit with the previous one after comparable wound areas are measured.</p>

              <div className="dfu-visit-heading">
                <h3>Visit images</h3>
                <span>{visits.length} {visits.length === 1 ? 'visit' : 'visits'}</span>
              </div>
              {visits.length === 0 ? (
                <p className="dfu-visits-empty">No visit images added yet.</p>
              ) : (
                <ol className="dfu-visit-list">
                  {visits.map((visit, index) => (
                    <li key={visit.date}>
                      <img src={visit.url} alt={`Wound image from ${displayDate(visit.date)}`} />
                      <div className="dfu-visit-info">
                        <strong>Visit {index + 1} <span>· {displayDate(visit.date)}</span></strong>
                        <span>{index === 0 ? 'Baseline · no previous comparison' : 'Change from previous visit · pending analysis'}</span>
                      </div>
                      <button type="button" onClick={() => removeVisit(visit.date)} aria-label={`Remove visit from ${displayDate(visit.date)}`}>Remove</button>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        </div>

        <div className="dfu-page-bottom">
          <p>Prototype only. Images and case details stay in this browser tab and disappear on refresh. Do not use this page for clinical decisions.</p>
          {visits.length > 0 && <button type="button" onClick={clearCase}>Start a different case</button>}
        </div>
      </div>
    </div>
  );
}
