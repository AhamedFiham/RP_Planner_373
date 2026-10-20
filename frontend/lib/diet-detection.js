export const MAX_MEAL_BYTES = 10 * 1024 * 1024;
export function validateMealFile(file) {
  if (!file || !/\.(jpe?g|png|webp)$/i.test(file.name) || (file.type && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type))) return 'Choose a JPG, JPEG, PNG or WebP image.';
  if (!file.size) return 'This file is empty. Choose another meal image.';
  if (file.size > MAX_MEAL_BYTES) return 'Choose an image smaller than 10 MiB.';
  return null;
}
export function validateGlucoseInput(glucose, unit = 'mg/dL') {
  const trimmed = typeof glucose === 'string' ? glucose.trim() : String(glucose ?? '').trim();
  if (!trimmed) return 'Enter a valid glucose value to receive meal guidance.';
  const num = Number(trimmed);
  if (!Number.isFinite(num) || num <= 0) return 'Enter a valid glucose value to receive meal guidance.';
  if (!['mg/dL', 'mmol/L'].includes(unit)) return 'Enter a valid glucose value to receive meal guidance.';
  return null;
}
export const foodLabel = name => name.replaceAll('_', ' ');
export function boxPosition(box, width, height) {
  return { left: `${box.x1 / width * 100}%`, top: `${box.y1 / height * 100}%`, width: `${(box.x2 - box.x1) / width * 100}%`, height: `${(box.y2 - box.y1) / height * 100}%` };
}
export function validateDetectionResponse(data) {
  const finite = Number.isFinite;
  if (!data || data.success !== true || !Number.isInteger(data.image_width) || data.image_width <= 0 || !Number.isInteger(data.image_height) || data.image_height <= 0 || !Array.isArray(data.detections) || data.detection_count !== data.detections.length) throw new Error('The service returned an unexpected response. Please try again.');
  for (const d of data.detections) {
    const b = d.bounding_box;
    if (!Number.isInteger(d.class_id) || d.class_id < 0 || d.class_id > 45 || typeof d.food_name !== 'string' || !d.food_name || !finite(d.confidence) || d.confidence < 0 || d.confidence > 1 || !b || ![b.x1,b.y1,b.x2,b.y2].every(finite) || !(0 <= b.x1 && b.x1 < b.x2 && b.x2 <= data.image_width && 0 <= b.y1 && b.y1 < b.y2 && b.y2 <= data.image_height)) throw new Error('The service returned an unexpected response. Please try again.');
  }
  return data;
}

export function validatePortionResponse(data) {
  const error = () => { throw new Error('The service returned an unexpected portion response. Please try again.'); };
  if (!data || !Array.isArray(data.foods) || !Array.isArray(data.portion_summary)) error();
  const normalized = validateDetectionResponse({ ...data, detections: data.foods });
  for (const food of [...data.foods, ...data.portion_summary]) {
    const p = food.portion || food;
    if (!['area_based','count_based','reference_based'].includes(p.method) || !['Small','Medium','Large','Unknown','Needs Calibration'].includes(p.portion_category) || p.estimated_grams !== null || p.validated !== false || (p.relative_area !== null && (!Number.isFinite(p.relative_area) || p.relative_area < 0 || p.relative_area > 1)) || (p.count !== null && (!Number.isInteger(p.count) || p.count < 0))) error();
  }
  return normalized;
}
export const portionMethodLabel = method => ({ area_based: 'Area Based', count_based: 'Count Based', reference_based: 'Reference Based' }[method]);
export const visibleAreaLabel = value => value === null ? 'Not applicable' : `${(value * 100).toFixed(1)}%`;

// Group only presentation; original detections and their boxes remain untouched.
export function groupedPortionFoods(detections, summaries = []) {
  const groups = new Map();
  for (const d of detections) {
    if (!groups.has(d.food_name)) groups.set(d.food_name, { ...d, observed_detection_count: 0 });
    const group = groups.get(d.food_name);
    group.confidence = Math.max(group.confidence, d.confidence);
    group.observed_detection_count++;
    if (!group.fast_food_guidance && d.fast_food_guidance) group.fast_food_guidance = d.fast_food_guidance;
    if (!group.gi && d.gi) group.gi = d.gi;
  }
  return [...groups.values()].map(group => {
    const summary = summaries.find(s => s.food_name === group.food_name && s.class_id === group.class_id);
    return { ...group, portion: summary || { method: group.portion?.method || 'reference_based', portion_category: 'Unknown', count: null, validated: false, estimated_grams: null } };
  }).sort((a,b) => b.confidence-a.confidence);
}
export const visualPortionLabel = category => ['Small','Medium','Large'].includes(category) ? category : 'Unknown';
export function portionCategoryCounts(detections, summaries) {
  return groupedPortionFoods(detections, summaries).reduce((counts, food) => {
    counts[visualPortionLabel(food.portion.portion_category)]++;
    return counts;
  }, { Small: 0, Medium: 0, Large: 0, Unknown: 0 });
}

export function patientAnalysisError(message) {
  if (/empty|format|JPG|JPEG|PNG|WebP|file|dimension|MiB|could not be opened/i.test(message)) return 'Please choose a clear JPG, PNG or WebP meal photo within the upload limits.';
  if (/connection|network/i.test(message)) return 'We can’t connect right now. Check your connection and try again.';
  if (/too long|timeout/i.test(message)) return 'This is taking longer than expected. Please try again.';
  return 'Please try again in a moment or choose another meal photo.';
}
