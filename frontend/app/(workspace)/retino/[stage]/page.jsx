import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import RetinoStepper from '@/components/retino/retino-stepper';

const stages = {
  quality: { step: 2, title: 'Quality Check & Preprocessing' },
  prediction: { step: 3, title: 'DR Severity Prediction' },
  probabilities: { step: 4, title: 'Five-Class Probabilities' },
  explain: { step: 5, title: 'Grad-CAM Explanation' },
  result: { step: 6, title: 'Final Result & Guidance' },
};

export async function generateMetadata({ params }) {
  const { stage: stageName } = await params;
  const stage = stages[stageName];
  return { title: stage ? `${stage.title} | Retinopathy` : 'Retinopathy' };
}

export default async function RetinoStagePage({ params }) {
  const { stage: stageName } = await params;
  if (stageName === 'quality') redirect('/retino/upload');

  const stage = stages[stageName];
  if (!stage) notFound();

  return (
    <div className="retino-page">
      <RetinoStepper currentStep={stage.step} />
      <header className="retino-heading-row">
        <div>
          <p className="retino-eyebrow">Retinal image screening workflow</p>
          <h1 className="retino-title">{stage.title}</h1>
          <p className="retino-subtitle">This workflow stage is planned and has not been implemented yet.</p>
        </div>
      </header>
      <section className="retino-pending-panel" aria-label="Stage status">
        <p>
          This interface is currently frontend-only. No image quality assessment, model prediction, probability analysis,
          or explanation is being performed here.
        </p>
        <Link className="retino-primary-button" href="/retino/upload">Return to image upload</Link>
      </section>
    </div>
  );
}