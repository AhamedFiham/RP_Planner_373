
"use client";

import { useState } from "react";

const fields = [
  {
    name: "pregnancies",
    label: "Pregnancies",
    help: "Number of previous pregnancies (optional)",
    min: 0,
    max: 17,
    step: 1,
    optional: true,
  },
  {
    name: "glucose",
    label: "Glucose",
    help: "Glucose measurement (mg/dL)",
    min: 1,
    max: 300,
    step: 0.1,
  },
  {
    name: "blood_pressure",
    label: "Blood pressure",
    help: "Diastolic pressure (mmHg)",
    min: 1,
    max: 200,
    step: 0.1,
  },
  {
    name: "skin_thickness",
    label: "Skin thickness",
    help: "Triceps skinfold measurement (mm)",
    min: 1,
    max: 100,
    step: 0.1,
  },
  {
    name: "insulin",
    label: "Insulin",
    help: "Insulin measurement (µU/mL)",
    min: 1,
    max: 1000,
    step: 0.1,
  },
  {
    name: "bmi",
    label: "Body mass index (BMI)",
    help: "Weight relative to height (kg/m²)",
    min: 1,
    max: 100,
    step: 0.1,
  },
  {
    name: "diabetes_pedigree_function",
    label: "Diabetes pedigree function",
    help: "Family-history-related dataset score",
    min: 0.001,
    max: 3,
    step: 0.001,
  },
  {
    name: "age",
    label: "Age",
    help: "Age in years",
    min: 21,
    max: 100,
    step: 1,
  },
];

const initialValues = Object.fromEntries(
  fields.map((field) => [field.name, ""])
);

export default function DiabetesForm({
  onPredict,
  loading,
}) {
  const [values, setValues] = useState(initialValues);

  function handleChange(event) {
    const { name, value } = event.target;

    setValues((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  function handleSubmit(event) {
    event.preventDefault();

    const measurements = Object.fromEntries(
      fields.map((field) => [
        field.name,
        values[field.name] === "" || values[field.name] === null || values[field.name] === undefined
          ? (field.optional ? 0 : 0)
          : Number(values[field.name]),
      ])
    );

    onPredict(measurements);
  }

  function handleReset() {
    setValues(initialValues);
  }

  return (
    <section className="diabetes-card">
      <div className="diabetes-card-heading">
        <div>
          <span className="diabetes-step">01</span>
          <h2>Patient measurements</h2>
          <p>
            Enter the eight measurements required by
            the research model.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="diabetes-form-grid">
          {fields.map((field) => (
            <div
              className="diabetes-field"
              key={field.name}
            >
              <label htmlFor={field.name}>
                {field.label}
                {field.optional ? (
                  <span className="optional-mark"> (optional)</span>
                ) : (
                  <span className="required-mark"> *</span>
                )}
              </label>

              <input
                id={field.name}
                name={field.name}
                type="number"
                value={values[field.name]}
                onChange={handleChange}
                min={field.min}
                max={field.max}
                step={field.step}
                placeholder={
                  field.optional
                    ? `Enter ${field.label.toLowerCase()} (optional)`
                    : `Enter ${field.label.toLowerCase()}`
                }
                required={!field.optional}
                disabled={loading}
              />

              <small>{field.help}</small>
            </div>
          ))}
        </div>

        <div className="diabetes-form-actions">
          <button
            type="submit"
            className="diabetes-primary-button"
            disabled={loading}
          >
            {loading
              ? "Analyzing measurements..."
              : "Predict diabetes risk"}
          </button>

          <button
            type="button"
            className="diabetes-secondary-button"
            onClick={handleReset}
            disabled={loading}
          >
            Clear form
          </button>
        </div>
      </form>

      <p className="diabetes-form-note">
        Enter actual measurements. Do not replace
        unavailable values with zero or estimates.
      </p>
    </section>
  );
}
