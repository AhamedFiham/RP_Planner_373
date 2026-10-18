export const MAX_MEAL_BYTES = 10 * 1024 * 1024;
export function validateMealFile(file) {
  if (!file || !/\.(jpe?g|png|webp)$/i.test(file.name) || (file.type && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type))) return 'Choose a JPG, JPEG, PNG or WebP image.';
  if (!file.size) return 'This file is empty. Choose another meal image.';
  if (file.size > MAX_MEAL_BYTES) return 'Choose an image smaller than 10 MiB.';
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
