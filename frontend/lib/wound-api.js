const API_URL = (process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export async function woundRequest(path, token, options = {}) {
  const { body, signal, method = 'GET', blob = false } = options;
  const headers = { Authorization: `Bearer ${token}` };
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  let response;
  try {
    response = await fetch(`${API_URL}/api/wound${path}`, {
      method, headers, signal, cache: 'no-store',
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach the clinic backend. Check that the API server is running.');
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join(' ') : data.detail;
    const error = new Error(response.status === 401 ? 'Your session has expired. Sign out and sign in again.' : detail || `Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return blob ? response.blob() : response.json();
}
