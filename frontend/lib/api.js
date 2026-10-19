// Add implementation here.

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

export async function predictDiabetes(patientData) {
  const response = await fetch(
    `${API_BASE_URL}/api/diabetes/predict`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(patientData),
    }
  );

  const result = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      result?.detail ||
      `Prediction request failed (${response.status})`;

    throw new Error(
      typeof message === "string"
        ? message
        : JSON.stringify(message)
    );
  }

  return result;
}
