'use client';

import { FileImage, ImagePlus, LoaderCircle, RefreshCw, UploadCloud, X } from 'lucide-react';
import { useRef } from 'react';
import { MAX_FILE_SIZE } from '@/lib/retinopathy/constants';

export default function RetinalImageUpload({ selectedImage, onSelect, onRemove, onAnalyze, status, error }) {
  const input = useRef(null);
  const isBusy = status === 'checking_quality' || status === 'analyzing';

  function acceptFiles(files) {
    if (isBusy || !files?.length) return;
    if (files.length !== 1) onSelect(null, 'Please upload one retinal image at a time.');
    else onSelect(files[0]);
  }

  return (
    <section className="retino-card retino-upload-card" aria-labelledby="upload-title" aria-busy={isBusy}>
      <div className="retino-card-heading">
        <div className="retino-icon teal"><UploadCloud size={20} /></div>
        <div><h2 id="upload-title">Upload Retinal Fundus Image</h2><p>Upload a clear retinal photograph for AI-assisted severity analysis.</p></div>
      </div>
      <input ref={input} id="retinal-file" hidden type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" disabled={isBusy}
        onChange={event => { acceptFiles(event.target.files); event.target.value = ''; }} />
      {!selectedImage ? (
        <button className="retino-dropzone" type="button" onClick={() => input.current.click()}
          onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); acceptFiles(event.dataTransfer.files); }}>
          <span className="retino-drop-icon"><ImagePlus size={25} /></span>
          <strong>Drop your fundus image here</strong>
          <span>or click to browse · JPG, JPEG, PNG · up to {MAX_FILE_SIZE / 1024 / 1024} MB</span>
        </button>
      ) : (
        <div className="retino-selected-file" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); acceptFiles(event.dataTransfer.files); }}>
          <div className="retino-file-thumb"><img src={selectedImage.url} alt="Selected retinal fundus preview" /></div>
          <div className="retino-file-copy"><strong>{selectedImage.file.name}</strong><span>{(selectedImage.file.size / 1024 / 1024).toFixed(2)} MB · Local preview</span></div>
          <button className="retino-icon-button" type="button" onClick={onRemove} aria-label={isBusy ? "Cancel and remove selected image" : "Remove selected image"}><X size={18} /></button>
        </div>
      )}
      {error && <p className="retino-error" role="alert">{error}</p>}
      <p className="retino-chart-note">Your image is sent through your authenticated session. If required models are unavailable, the server rejects the request before saving the image or creating an assessment.</p>
      <div className="retino-upload-actions">
        <button className="retino-button primary" type="button" onClick={onAnalyze} disabled={!selectedImage || isBusy}>
          {isBusy ? <><LoaderCircle className="retino-spin" size={17} />Analyzing retinal image…</> : <><FileImage size={17} />Analyze Retinal Image</>}
        </button>
        {selectedImage && <button className="retino-button ghost" type="button" onClick={() => input.current.click()} disabled={isBusy}><RefreshCw size={16} />Replace image</button>}
      </div>
      <p className="retino-visually-hidden" role="status">{isBusy ? 'Retinal analysis in progress.' : ''}</p>
    </section>
  );
}
