
export default function RiskResult({ result }) {
  if (!result) {
    return (
      <section className="diabetes-card diabetes-empty-result">
        <div className="diabetes-result-icon">+</div>
        <h2>Your prediction result</h2>
        <p>
          Complete the patient measurements and select
          Predict diabetes risk to see the model output.
        </p>
        <div className="diabetes-empty-indicator">
          Waiting for assessment
        </div>
      </section>
    );
  }

  const prediction = Number(result.predicted_class);
  const probability = Number(result.probability_class_1);

  const hasProbability =
    Number.isFinite(probability) &&
    probability >= 0 &&
    probability <= 1;

  const explanations = Array.isArray(result.explanations)
    ? result.explanations
    : [];

  const awareness = result.awareness;

  return (
    <section className="diabetes-card">
      <div className="diabetes-card-heading">
        <div>
          <span className="diabetes-step">02</span>
          <h2>Prediction result</h2>
          <p>Output from your trained machine-learning model.</p>
        </div>

        <span className="diabetes-model-badge">
          {result.model_name || "Trained model"}
        </span>
      </div>

      <div className="diabetes-prediction-summary">
        <div
          className={`diabetes-result-icon ${
            prediction === 1 ? "result-warning" : "result-positive"
          }`}
        >
          {prediction === 1 ? "!" : "✓"}
        </div>

        <div>
          <span className="diabetes-result-label">
            Model classification
          </span>

          <h3>
            {prediction === 1
              ? "Positive classification"
              : "Negative classification"}
          </h3>

          <p>
            {prediction === 1
              ? "The model classified these measurements as Outcome 1."
              : "The model classified these measurements as Outcome 0."}
          </p>
        </div>
      </div>

      {hasProbability && (
        <div className="diabetes-probability-box">
          <div className="diabetes-probability-heading">
            <span>Model probability for Outcome 1</span>
            <strong>
              {(probability * 100).toFixed(1)}%
            </strong>
          </div>

          <div
            className="diabetes-progress-track"
            role="progressbar"
            aria-label="Model probability for Outcome 1"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(probability * 100)}
          >
            <div
              className="diabetes-progress-fill"
              style={{ width: `${probability * 100}%` }}
            />
          </div>

          <small>
            This is the model's estimated probability for
            class 1, not a clinically calibrated personal
            diabetes risk.
          </small>
        </div>
      )}

      <div className="diabetes-explanation-section">
        <h3>Important model factors</h3>

        {explanations.length === 0 ? (
          <p>No feature explanations were returned.</p>
        ) : (
          <div className="diabetes-explanation-list">
            {explanations.map((item) => (
              <div
                className="diabetes-explanation-row"
                key={item.feature}
              >
                <div>
                  <strong>{item.feature}</strong>
                  <small>
                    Observed value:{" "}
                    {item.observed_value == null
                      ? "Unavailable"
                      : item.observed_value}
                  </small>
                </div>

                <span
  className={
    item.direction === "increases_model_output"
      ? "factor-increases"
      : item.direction === "decreases_model_output"
        ? "factor-decreases"
        : ""
  }
>
  {item.direction === "increases_model_output"
    ? "Increases output"
    : item.direction === "decreases_model_output"
      ? "Decreases output"
      : "Direction unavailable"}
</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {awareness?.highlighted_factors?.length > 0 && (
        <div className="diabetes-awareness">
          <h3>{awareness.title}</h3>

          {awareness.highlighted_factors.map((factor) => (
            <div key={factor.feature}>
              <strong>{factor.label}</strong>
              <p>{factor.awareness_message}</p>
            </div>
          ))}
        </div>
      )}

      <p className="diabetes-disclaimer">
        {result.disclaimer ||
          awareness?.important_notice ||
          "This experimental research tool is not a medical diagnosis. Consult a qualified healthcare professional for assessment and medical decisions."}
      </p>
    </section>
  );
}
