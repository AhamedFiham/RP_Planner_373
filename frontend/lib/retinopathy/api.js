// Reuse the existing login API origin and AuthProvider token; never persist another token.
const BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
export class ApiError extends Error {
  constructor(message, status, code, assessmentId) { super(message); this.status = status; this.code = code; this.assessmentId = assessmentId; }
}
export function errorMessage(status, code) {
  if (status === 401) return 'Your session has expired. Please sign in again.';
  if (status === 404) return 'This assessment or image is no longer available.';
  if (status === 413) return 'The image exceeds the allowed size. Please select a smaller image.';
  if (status === 415 || status === 422) return 'Please select a readable JPG or PNG retinal image within the upload limits.';
  if (code === 'inference_busy') return 'The analysis service is busy. Please try again later.';
  if (status === 504) return 'Analysis timed out. Check history before retrying.';
  if (code?.includes('model') || code === 'configuration_unavailable') return 'The retinal analysis service is currently unavailable. Required models are not ready.';
  if (status === 503) return 'The assessment service is unavailable. Please try again later.';
  return 'Unable to complete the request. Please try again.';
}
export function artifactPath(path) {
  // Never send a bearer token to a returned external URL or arbitrary endpoint.
  if (typeof path !== 'string' || !/^\/api\/retinopathy\/(?:assessments\/[a-f\d]{24}\/artifacts\/[a-f\d]{24}|artifacts\/[a-f\d]{32}\/(?:original|model_input|class_[0-4]_(?:heatmap|overlay))\.png)$/.test(path)) throw new ApiError('Invalid protected image reference.', 0, 'invalid_artifact');
  return path;
}
export function createRetinopathyApi(token, onUnauthorized = () => {}) {
  async function request(path, { signal, body, method = 'GET', blob = false } = {}) {
    if (!token) throw new ApiError('Please sign in to continue.', 401, 'unauthorized');
    let response;
    try { response = await fetch(BASE + path, { method, body, signal, cache: 'no-store', headers: { Authorization: `Bearer ${token}` } }); }
    catch (error) { if (error.name === 'AbortError' || signal?.aborted) throw error; throw new ApiError('Unable to connect to the analysis service.', 0, 'network'); }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      if (response.status === 401) onUnauthorized();
      throw new ApiError(errorMessage(response.status, data.status), response.status, data.status, data.assessment_id);
    }
    if (response.status === 204) return null;
    if (blob) { if (!response.headers.get('content-type')?.startsWith('image/png')) throw new ApiError('Image unavailable.', 0, 'invalid_artifact'); return response.blob(); }
    return response.json();
  }
  const id = value => { if (!/^[a-f\d]{24}$/i.test(value)) throw new ApiError('Invalid assessment identifier.', 404); return value; };
  return {
    health: signal => request('/api/retinopathy/health', { signal }),
    analyze: (file, signal) => { const body = new FormData(); body.append('image', file); return request('/api/retinopathy/analyze', { method: 'POST', body, signal }); },
    history: (page = 1, signal) => request(`/api/retinopathy/history?page=${page}&limit=10`, { signal }),
    detail: (value, signal) => request(`/api/retinopathy/assessments/${id(value)}`, { signal }),
    remove: (value, signal) => request(`/api/retinopathy/assessments/${id(value)}`, { method: 'DELETE', signal }),
    artifact: (path, signal) => request(artifactPath(path), { signal, blob: true }),
  };
}
