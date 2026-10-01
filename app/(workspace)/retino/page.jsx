import Link from 'next/link';

export const metadata = { title: 'Retinopathy' };

export default function RetinoPage() {
  return (
    <>
      <Link className="back-link" href="/home">← Back to home</Link>
      <h1>Retinopathy</h1>
      <p className="muted">Diabetic retinopathy detection research</p>

      <section className="content-box" aria-labelledby="retino-heading">
        <h2 id="retino-heading">Your work area</h2>
        <p>This section is ready for your retinopathy workflows, imaging records, and model outputs.</p>
        <ul className="feature-list">
          <li>Patient retinal history</li>
          <li>Retinal image uploads and visits</li>
          <li>Severity prediction and clinical insights</li>
        </ul>
        <p className="muted">These features are planned and will be added later.</p>
      </section>
    </>
  );
}
