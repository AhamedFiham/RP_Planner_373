'use client';

import { useRef, useState } from 'react';
import { useRetinoWorkflow } from './retino-workflow';

const MAX_FILE_SIZE = 10 * 1024 * 1024;
const VALID_EXTENSIONS = ['jpg', 'jpeg', 'png'];
const VALID_TYPES = ['image/jpeg', 'image/png'];

function formatFileSize(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FundusUploader() {
  const inputRef = useRef(null);
  const { workflow, setUploadedImage, clearUploadedImage, isRestoring } = useRetinoWorkflow();
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  async function acceptFile(file) {
    if (!file) return;
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!VALID_EXTENSIONS.includes(extension) || (file.type && !VALID_TYPES.includes(file.type))) {
      setError('Choose an image in JPG, JPEG, or PNG format.');
      return;
    }
    if (file.size === 0 || file.size > MAX_FILE_SIZE) {
      setError(file.size > MAX_FILE_SIZE
        ? 'The image must be 10 MB or smaller.'
        : 'The selected image is empty. Choose another file.');
      return;
    }

    setError('');
    setIsSaving(true);
    try {
      await setUploadedImage(file);
    } catch {
      setError('The image could not be saved in this browser. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }

  function handleInputChange(event) {
    acceptFile(event.target.files?.[0]);
    event.target.value = '';
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    acceptFile(event.dataTransfer.files?.[0]);
  }

  async function removeImage() {
    setError('');
    try {
      await clearUploadedImage();
    } catch {
      setError('The saved image could not be removed. Please try again.');
    }
  }

  const image = workflow.uploadedImage;

  return (
    <>
      <section className="retino-card" aria-labelledby="retino-upload-heading">
        <div className="retino-card-heading">
          <span className="retino-card-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M4 16.5 8.5 12l3 3 3.5-4 5 5.5" />
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
            </svg>
          </span>
          <div>
            <h2 id="retino-upload-heading">Upload Fundus Image</h2>
            <p>Select one retinal image to begin the workflow.</p>
          </div>
        </div>

        <label
          className={`retino-dropzone${isDragging ? ' is-dragging' : ''}`}
          htmlFor="retino-fundus-image"
          onDragEnter={event => { event.preventDefault(); setIsDragging(true); }}
          onDragOver={event => event.preventDefault()}
          onDragLeave={event => {
            if (!event.currentTarget.contains(event.relatedTarget)) setIsDragging(false);
          }}
          onDrop={handleDrop}
        >
          <input
            ref={inputRef}
            className="retino-file-input"
            id="retino-fundus-image"
            type="file"
            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            aria-describedby={error ? 'retino-upload-error' : 'retino-file-limits'}
            onChange={handleInputChange}
            disabled={isSaving || isRestoring}
          />
          <div className="retino-dropzone-content">
            <span className="retino-eye-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path d="M2.5 12s3.3-6 9.5-6 9.5 6 9.5 6-3.3 6-9.5 6-9.5-6-9.5-6Z" />
                <circle cx="12" cy="12" r="3" />
                <circle cx="12" cy="12" r="1" fill="currentColor" />
              </svg>
            </span>
            <span className="retino-dropzone-instructions">
              <span className="retino-dropzone-title">Upload Fundus Image</span>
              <span className="retino-dropzone-copy">Drag and drop your retinal image here, or click to browse.</span>
            </span>
            <span className="retino-browse-button" aria-hidden="true">Browse image</span>
            <span className="retino-file-limits" id="retino-file-limits">JPG, JPEG, or PNG · Maximum file size 10 MB</span>
          </div>
        </label>

        {error && <p className="retino-upload-error" id="retino-upload-error" role="alert">{error}</p>}
        {(isSaving || isRestoring) && <p className="retino-file-limits" role="status">{isRestoring ? 'Restoring saved image…' : 'Saving image…'}</p>}
      </section>

      {image && workflow.imagePreview && (
        <section className="retino-card" aria-labelledby="retino-uploaded-heading">
          <div className="retino-uploaded-card">
            <div className="retino-preview-frame">
              <img src={workflow.imagePreview} alt="Uploaded retinal fundus image preview" />
            </div>
            <div className="retino-image-details">
              <h3 id="retino-uploaded-heading">Uploaded Image</h3>
              <p className="retino-image-name">{image.name}</p>
              <p className="retino-image-meta">
                <span>{image.type || 'Image'}</span>
                <span>{formatFileSize(image.size)}</span>
              </p>
              <div className="retino-image-actions">
                <button className="retino-secondary-button" type="button" onClick={() => inputRef.current?.click()} disabled={isSaving || isRestoring}>
                  Replace image
                </button>
                <button className="retino-secondary-button" type="button" onClick={removeImage} disabled={isSaving || isRestoring}>
                  Remove
                </button>
              </div>
            </div>
          </div>
        </section>
      )}
    </>
  );
}