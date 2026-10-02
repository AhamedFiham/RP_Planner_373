import Link from 'next/link';

export const metadata = {
  title: { absolute: 'DCare AI | Home' },
  description: 'Explore DCare AI research on diabetic foot ulcers, retinopathy, and related care.',
};

const researchAreas = [
  {
    number: '01',
    title: 'Diabetic foot ulcers',
    tag: 'DFU research',
    description: 'Exploring how patient and visit information could help us understand wound healing over time.',
    href: '/dfu',
    action: 'Explore DFU',
  },
  {
    number: '02',
    title: 'Diabetic retinopathy',
    tag: 'Retinopathy research',
    description: 'A space for our team’s work on retinal images, clinical records, and future analysis.',
    href: '/retino',
    action: 'Explore retinopathy',
  },
];

export default function HomePage() {
  return (
    <div className="home-page">
      <div className="home-visual-space" aria-hidden="true" />

      <section className="home-intro" aria-labelledby="home-title">
        <p className="home-eyebrow"><span aria-hidden="true" /> DCare AI · Research in progress</p>
        <h1 id="home-title">Research for better<br />diabetes care.</h1>
        <p className="home-intro-copy">
          One place for our team’s work on diabetic foot ulcers, retinopathy, and the ideas we’re developing together.
        </p>
        <a className="home-intro-link" href="#our-work">Explore our work <span aria-hidden="true">↗</span></a>
      </section>

      <section className="home-work" id="our-work" aria-labelledby="home-work-title">
        <div className="home-work-heading">
          <p className="home-eyebrow"><span aria-hidden="true" /> Our work</p>
          <h2 id="home-work-title">Explore the research.</h2>
          <p>Choose a section to see what each part of the project is becoming.</p>
        </div>

        <div className="home-research-grid">
          {researchAreas.map(area => (
            <Link className="home-research-card" href={area.href} key={area.href}>
              <span className="home-research-top"><span>{area.tag}</span><span>{area.number} / 02</span></span>
              <span className="home-research-body">
                <span className="home-research-title">{area.title}</span>
                <span className="home-research-copy">{area.description}</span>
              </span>
              <span className="home-research-action">{area.action} <span aria-hidden="true">↗</span></span>
            </Link>
          ))}
        </div>

        <div className="home-team">
          <div>
            <p className="home-eyebrow"><span aria-hidden="true" /> Team spaces</p>
            <h3>More from the team</h3>
          </div>
          <div className="home-team-links">
            {[1, 2, 3].map(member => (
              <Link href={`/members/${member}`} key={member}>
                <span>Member {member}</span><span aria-hidden="true">↗</span>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
