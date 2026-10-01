import Link from 'next/link';
import WelcomeMessage from '@/components/welcome-message';

export const metadata = { title: 'Home' };

export default function HomePage() {
  return (
    <>
      <h1>Home</h1>
      <WelcomeMessage />
      <h2>Project modules</h2>
      <p className="muted">Select a section to open your work area.</p>
      <div className="module-grid">
        <article className="module-card">
          <p className="module-owner">Your section</p>
          <h3>DFU</h3>
          <p>Diabetic foot ulcer wound healing research.</p>
          <Link className="button" href="/dfu">Open DFU</Link>
        </article>

        <article className="module-card">
          <p className="module-owner">Your section</p>
          <h3>Retinopathy</h3>
          <p>Diabetic retinopathy detection research.</p>
          <Link className="button" href="/retino">Open Retinopathy</Link>
        </article>

        {[1, 2].map(member => (
          <article className="module-card" key={member}>
            <p className="module-owner">Team section</p>
            <h3>Member {member}</h3>
            <p>A work area for Member {member}.</p>
            <Link className="button secondary" href={`/members/${member}`} aria-label={`Open Member ${member} section`}>Open section</Link>
          </article>
        ))}
      </div>
    </>
  );
}
