'use client';

import { useRetinoWorkflow } from './retino-workflow';

const steps = ['Upload', 'Quality', 'Prediction', 'Probabilities', 'Explain', 'Result'];

export default function RetinoStepper({ currentStep }) {
  const { workflow } = useRetinoWorkflow();

  return (
    <ol className="retino-stepper" aria-label="Retinopathy analysis progress">
      {steps.map((label, index) => {
        const stepNumber = index + 1;
        const isComplete = stepNumber === 1 && currentStep > 1 && Boolean(workflow.uploadedImage);
        const state = stepNumber === currentStep ? 'is-current' : isComplete ? 'is-complete' : '';
        return (
          <li
            className={`retino-step ${state}`.trim()}
            aria-current={stepNumber === currentStep ? 'step' : undefined}
            key={label}
          >
            <span className="retino-step-marker" aria-hidden="true">
              {isComplete ? '✓' : stepNumber}
            </span>
            <span className="retino-step-label">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}