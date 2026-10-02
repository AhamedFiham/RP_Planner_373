'use client';

import { useRouter } from 'next/navigation';
import FundusUploader from '@/components/retino/fundus-uploader';
import { useRetinoWorkflow } from '@/components/retino/retino-workflow';

export default function RetinoUploadPage() {
  const router = useRouter();
  const { workflow, isRestoring } = useRetinoWorkflow();

  return (
    <div className="retino-page">
      <header className="retino-heading-row retino-upload-heading-row">
        <div>
          <p className="retino-eyebrow">Retinal image screening workflow</p>
          <h1 className="retino-title">Diabetic Retinopathy Analysis</h1>
          <p className="retino-subtitle">
            Upload a retinal fundus image, then review its quality and preprocessing status before continuing.
          </p>
        </div>
        <div className={`retino-intake-status${workflow.uploadedImage ? ' is-ready' : ''}`} role="status" aria-live="polite">
          <span className="retino-intake-indicator" aria-hidden="true" />
          <span>
            <strong>{workflow.uploadedImage ? 'Image added' : 'Awaiting image'}</strong>
            <small>{workflow.uploadedImage ? 'Quality review pending' : 'Upload and image review'}</small>
          </span>
        </div>
      </header>

      <p className="retino-safety-note">
        <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 3 20 6v5c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6l8-3Z" />
          <path d="M12 8v4m0 3h.01" />
        </svg>
        <span>This system provides AI-assisted screening support and is not a medical diagnosis.</span>
      </p>

      <div className="retino-content-grid">
        <div className="retino-primary-column">
          <FundusUploader />
          <section className="retino-card retino-quality-panel" aria-labelledby="retino-quality-title">
            <div className="retino-card-heading">
              <span className="retino-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M4 6h16M4 12h16M4 18h16" />
                  <circle cx="8" cy="6" r="1.5" fill="white" />
                  <circle cx="15" cy="12" r="1.5" fill="white" />
                  <circle cx="10" cy="18" r="1.5" fill="white" />
                </svg>
              </span>
              <div>
                <h2 id="retino-quality-title">Image Quality &amp; Preprocessing</h2>
                <p>This review is combined with image upload on Page 1.</p>
              </div>
            </div>

            <div className="retino-quality-grid">
              <div className="retino-quality-item">
                <span className="retino-quality-label">Image quality check</span>
                <strong>{workflow.uploadedImage ? 'Not assessed' : 'Waiting for image'}</strong>
                <p>No automated focus, illumination, or suitability assessment is connected yet.</p>
              </div>
              <div className="retino-quality-item">
                <span className="retino-quality-label">Image preprocessing</span>
                <strong>Not applied</strong>
                <p>The uploaded image remains unchanged in this frontend demonstration.</p>
              </div>
            </div>
          </section>
          <div className="retino-continue-row">
            <button
              className="retino-primary-button"
              type="button"
              onClick={() => router.push('/retino/prediction')}
              disabled={!workflow.uploadedImage || isRestoring}
            >
              Continue to Prediction
              <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14m-6-6 6 6-6 6" />
              </svg>
            </button>
          </div>
        </div>

        <aside className="retino-aside-column" aria-label="Workflow information">
          <section className="retino-card retino-workflow-card" aria-labelledby="retino-workflow-title">
            <div className="retino-card-heading">
              <span className="retino-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path d="M4 5h16M4 12h16M4 19h16" />
                  <circle cx="8" cy="5" r="1.5" fill="white" />
                  <circle cx="15" cy="12" r="1.5" fill="white" />
                  <circle cx="10" cy="19" r="1.5" fill="white" />
                </svg>
              </span>
              <div>
                <h2 id="retino-workflow-title">Analysis Workflow</h2>
                <p>Six stages in one retinal analysis process</p>
              </div>
            </div>
            <ol className="retino-workflow-list">
              {[
                'Image Quality Check',
                'Image Preprocessing',
                'DR Severity Prediction',
                'Five-Class Probability Analysis',
                'Grad-CAM Explanation',
                'Guidance',
              ].map((label, index) => (
                <li className="retino-workflow-item" key={label}>
                  <span className="retino-workflow-number">{index + 1}</span>
                  <div><strong>{label}</strong></div>
                </li>
              ))}
            </ol>
          </section>

          <section className="retino-card retino-image-note" aria-labelledby="retino-image-note-title">
            <h2 id="retino-image-note-title">What happens to your image?</h2>
            <p>The image will first be checked for suitability before any severity prediction is generated.</p>
          </section>
        </aside>
      </div>
    </div>
  );
}