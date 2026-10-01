import Link from 'next/link';

export const metadata = { title: 'DFU' };

export default function DfuPage() {
  return (
    <>
      <Link className="back-link" href="/home">← Back to home</Link>
      <h1>DFU</h1>
      <p className="muted">Diabetic foot ulcer wound healing research</p>
      <section className="content-box" aria-labelledby="dfu-heading">
        <h2 id="dfu-heading">Your work area</h2>
        <p>This section is ready for your DFU features. You can add them as your dataset and model develop.</p>
        <ul className="feature-list">
          <li>Patient and wound details</li>
          <li>Visit records and wound images</li>
          <li>Healing prediction results</li>
        </ul>
        <p className="muted">These features are planned and will be added later.</p>
      </section>
    </>
  );
}
