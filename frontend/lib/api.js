import { validateConsumedResponse } from './consumed-nutrition.js';
import { validateNutritionRecords } from './nutrition-reference.js';
import { validateDetectionResponse, validatePortionResponse } from './diet-detection.js';
import { validateGIRecords } from './gi-reference.js';

// Matches the existing login configuration; keep backend configuration in one place for this API.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
export const detectMeal = (file, options) => analyzeImage(file, options, 'detect-food');
export const estimateMealConsumedNutrition = (file, options) => analyzeImage(file, options, 'estimate-consumed-nutrition');
export const analyzeMealGuidance = (file, options) => analyzeImage(file, options, 'analyze-meal-guidance');
export const mapMealNutrition = (file, options) => analyzeImage(file, options, 'map-nutrition');
export const mapMealGI = (file, options) => analyzeImage(file, options, 'map-gi');
export const estimateMealPortions = (file, options) => analyzeImage(file, options, 'estimate-portions');
async function analyzeImage(file, { signal, currentGlucose, glucoseUnit } = {}, endpoint) {
  const form = new FormData();
  form.append('image', file);
  if (endpoint === 'analyze-meal-guidance') { form.append('current_glucose', String(currentGlucose)); form.append('glucose_unit', glucoseUnit || 'mg/dL'); }
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
  return endpoint === 'analyze-meal-guidance' || endpoint === 'estimate-consumed-nutrition'
    ? validateConsumedResponse(data)
    : endpoint === 'map-gi'
    ? validateGIRecords(validateNutritionRecords(validatePortionResponse(data)))
    : endpoint === 'map-nutrition'
    ? validateNutritionRecords(validatePortionResponse(data))
    : endpoint === 'estimate-portions'
    ? validatePortionResponse(data)
    : validateDetectionResponse(data);
}
