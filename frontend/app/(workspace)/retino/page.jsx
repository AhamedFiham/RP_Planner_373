import Link from 'next/link';

export const metadata = { title: 'Retinopathy Dashboard' };

export default function RetinoPage() {
  return (
    <div className="retino-page retino-dashboard">
      <header className="retino-heading-row">
        <div>
          <p className="retino-eyebrow">Analysis workspace</p>
          <h1 className="retino-title">Retinopathy Dashboard</h1>
          <p className="retino-subtitle">
            Review sample records or begin an AI-assisted retinal image screening workflow.
          </p>
        </div>
      </header>

      <section className="retino-dashboard-launch" aria-labelledby="retino-launch-title">
        <div className="retino-launch-copy">
          <p className="retino-launch-label">New analysis</p>
          <h2 id="retino-launch-title">Begin with a fundus image</h2>
          <p>Upload one retinal image to start the quality check and preprocessing workflow.</p>
        </div>
        <div className="retino-launch-action">
          <span>Required input</span>
          <strong>JPG, JPEG, or PNG · Up to 10 MB</strong>
          <Link className="retino-dashboard-cta" href="/retino/upload">
            Upload an image
            <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14m-6-6 6 6-6 6" />
            </svg>
          </Link>
        </div>
      </section>

      <section className="retino-patients-panel" aria-labelledby="retino-patients-title">
        <div className="retino-dashboard-section-heading">
          <div>
            <p className="retino-eyebrow">Synthetic records</p>
            <h2 id="retino-patients-title">Sample patients</h2>
          </div>
          <span>Frontend demonstration only</span>
        </div>

        <p className="retino-demo-notice">
          These demonstration records are fictional and are not connected to real patients, images, or analysis results.
        </p>

        <div className="retino-patient-table-wrap" tabIndex={0} aria-label="Scrollable sample patient table">
          <table className="retino-patient-table">
            <thead>
              <tr>
                <th scope="col">Sample ID</th>
                <th scope="col">Patient</th>
                <th scope="col">Age</th>
                <th scope="col">Last visit</th>
                <th scope="col">Image status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>DEMO-001</td>
                <td>Sample Patient A</td>
                <td>58</td>
                <td><time dateTime="2026-09-26">Sep 26, 2026</time></td>
                <td><span className="retino-record-status">Upload needed</span></td>
              </tr>
              <tr>
                <td>DEMO-002</td>
                <td>Sample Patient B</td>
                <td>64</td>
                <td><time dateTime="2026-09-18">Sep 18, 2026</time></td>
                <td><span className="retino-record-status is-ready">Demo image</span></td>
              </tr>
              <tr>
                <td>DEMO-003</td>
                <td>Sample Patient C</td>
                <td>51</td>
                <td><time dateTime="2026-09-03">Sep 03, 2026</time></td>
                <td><span className="retino-record-status">Upload needed</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <p className="retino-dashboard-disclaimer">
        AI-assisted screening support only. This system does not provide a medical diagnosis.
      </p>
    </div>
  );
}
