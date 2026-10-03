import Link from 'next/link';
import { notFound } from 'next/navigation';

const members = ['1', '2', '3'];

export function generateStaticParams() {
  return members.map(member => ({ member }));
}

export async function generateMetadata({ params }) {
  const { member } = await params;
  return { title: members.includes(member) ? `Member ${member}` : 'Section not found' };
}

export default async function MemberPage({ params }) {
  const { member } = await params;
  if (!members.includes(member)) notFound();

  return (
    <>
      <Link className="back-link" href="/dashboard">← Back to dashboard</Link>
      <h1>Member {member}</h1>
      <p className="muted">Team member work area</p>
      <section className="content-box" aria-labelledby="member-heading">
        <h2 id="member-heading">Module content</h2>
        <p>This section is reserved for Member {member}&apos;s part of the research project.</p>
        <p className="muted">The module name and features can be added later.</p>
      </section>
    </>
  );
}
