
"use client";

import DiabetesForm from "../../components/diabetes/DiabetesForm";
import RiskResult from "../../components/diabetes/RiskResult";
import useDiabetesPrediction from "../../hooks/useDiabetesPrediction";

export default function DiabetesRiskPredictionPage() {
  const {
    result,
    loading,
    error,
    runPrediction,
  } = useDiabetesPrediction();

  return (
    <main className="diabetes-page">
      <div className="diabetes-page-inner">
        <div className="diabetes-page-heading">
          <p className="diabetes-eyebrow">
            DiaCare AI / AI Health Tools
          </p>

          <h1>Diabetes Risk Prediction</h1>

          <p>
            Enter patient measurements to receive an
            explainable machine-learning assessment and
            personalized health-awareness information.
          </p>
        </div>

        <div className="diabetes-notice">
          <strong>Research decision-support tool</strong>
          <p>
            This experimental model is not a clinically
            validated diagnostic tool. Its output should
            not replace assessment by a qualified
            healthcare professional.
          </p>
        </div>

        {error && (
          <div className="diabetes-error" role="alert">
            <strong>Prediction could not be completed</strong>
            <p>{error}</p>
            <small>
              Check that the backend is running and that
              its request schema matches the frontend.
            </small>
          </div>
        )}

        <div className="diabetes-workspace">
          <DiabetesForm
            onPredict={runPrediction}
            loading={loading}
          />

          <RiskResult result={result} />
        </div>

        <p className="diabetes-page-footer">
          DiaCare AI · Experimental diabetes risk research
        </p>
      </div>
    </main>
  );
}
