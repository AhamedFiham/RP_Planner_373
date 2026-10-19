import { validateConsumedResponse } from './consumed-nutrition.js';
import { validateNutritionRecords } from './nutrition-reference.js';
import { validateDetectionResponse, validatePortionResponse } from './diet-detection.js';

// Matches the existing login configuration; keep backend configuration in one place for this API.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
export const detectMeal = (file, options) => analyzeImage(file, options, 'detect-food');
export const estimateMealConsumedNutrition = (file, options) => analyzeImage(file, options, 'estimate-consumed-nutrition');
export const mapMealNutrition = (file, options) => analyzeImage(file, options, 'map-nutrition');
export const estimateMealPortions = (file, options) => analyzeImage(file, options, 'estimate-portions');
async function analyzeImage(file, { signal } = {}, endpoint) {
  const form = new FormData();
  form.append('image', file);
  let response;
  try {
    // The browser sets the multipart boundary; do not set Content-Type manually.
    response = await fetch(`${API_URL}/api/diet/${endpoint}`, { method: 'POST', body: form, signal });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Food detection service is unavailable. Check your connection and try again.');
  }
  if (!response.ok) throw new Error(response.status === 400 ? "We couldn't analyze this image. Choose a valid meal image with visible food items." : 'Food detection service is currently unavailable. Please try again shortly.');
  let data;
  try { data = await response.json(); } catch { throw new Error('The service returned an unexpected response. Please try again.'); }
  return endpoint === 'estimate-consumed-nutrition' ? validateConsumedResponse(data) : endpoint === 'map-nutrition' ? validateNutritionRecords(validatePortionResponse(data)) : endpoint === 'estimate-portions' ? validatePortionResponse(data) : validateDetectionResponse(data);
}
