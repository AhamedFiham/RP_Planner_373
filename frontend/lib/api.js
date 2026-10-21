/**
 * DiaCare API Client for Diabetes Risk Assessment & ML Explainability
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

function getAuthHeaders(token) {
  const headers = { 'Content-Type': 'application/json' };
  const storedToken = token || (typeof window !== 'undefined' ? window.localStorage.getItem('dcare_token') : null);
  if (storedToken) {
    headers['Authorization'] = `Bearer ${storedToken}`;
  }
  return headers;
}

export async function predictDiabetesRisk(patientData, token) {
  const res = await fetch(`${API_BASE}/api/diabetes/predict`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify(patientData),
  });

  if (!res.ok) {
    let errorMsg = `Server error (${res.status})`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        if (Array.isArray(errJson.detail)) {
          errorMsg = errJson.detail.map((d) => d.msg || `${d.loc?.join('.')}: invalid`).join(', ');
        } else {
          errorMsg = errJson.detail;
        }
      }
    } catch (_) {}
    throw new Error(errorMsg);
  }

  return await res.json();
}

export async function fetchDiabetesHistory(token, limit = 20) {
  const res = await fetch(`${API_BASE}/api/diabetes/history?limit=${limit}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  });

  if (!res.ok) {
    throw new Error(`Failed to load assessment history (${res.status})`);
  }

  return await res.json();
}

export async function fetchDiabetesModelInfo() {
  const res = await fetch(`${API_BASE}/api/diabetes/model-info`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!res.ok) {
    throw new Error(`Failed to load model metadata (${res.status})`);
  }

  return await res.json();
}
