
"use client";

import { useState } from "react";
import { predictDiabetes } from "../lib/api";

export default function useDiabetesPrediction() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runPrediction(measurements) {
    setLoading(true);
    setError(null);
    setResult(null);

    // Convert frontend field names into the backend's expected names.
    const payload = {
      Pregnancies:
        measurements.pregnancies === "" ||
        measurements.pregnancies === null ||
        measurements.pregnancies === undefined ||
        isNaN(Number(measurements.pregnancies))
          ? 0
          : Number(measurements.pregnancies),
      Glucose: Number(measurements.glucose),
      BloodPressure: Number(measurements.blood_pressure),
      SkinThickness: Number(measurements.skin_thickness),
      Insulin: Number(measurements.insulin),
      BMI: Number(measurements.bmi),
      DiabetesPedigreeFunction: Number(
        measurements.diabetes_pedigree_function
      ),
      Age: Number(measurements.age),
    };

    try {
      // Use the API helper that already exists in lib/api.js.
      const response = await predictDiabetes(payload);

      setResult(response);
      return response;
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to complete the prediction."
      );

      return null;
    } finally {
      setLoading(false);
    }
  }

  return {
    result,
    loading,
    error,
    runPrediction,
  };
}
