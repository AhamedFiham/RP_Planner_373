import { CLASS_KEYS, RETINOPATHY_SEVERITIES } from './constants.js';
export function normalizeAnalysis(data) {
  if (!['completed', 'partial', 'quality_rejected'].includes(data?.status)) throw new Error('Unexpected analysis response.');
  const quality = data.image_quality;
  const qualityLabels = ['Unacceptable', 'Acceptable'];
  const qualityKeys = ['Unacceptable', 'Acceptable'];
  const qualityValues = qualityKeys.map(key => quality?.probabilities?.[key]);
  if (!quality || !qualityLabels.includes(quality.label) || !Number.isInteger(quality.class_id) || quality.class_id < 0 || quality.class_id > 1 ||
      quality.label !== qualityLabels[quality.class_id] || !Number.isFinite(quality.confidence) ||
      !qualityValues.every(value => Number.isFinite(value) && value >= 0 && value <= 1) ||
      Math.abs(qualityValues.reduce((a,b) => a+b, 0)-1) > 0.00001 ||
      Math.abs(quality.confidence-qualityValues[quality.class_id]) > 0.00001 ||
      typeof quality.model_version !== 'string') throw new Error('Invalid quality response.');
  if (data.status === 'quality_rejected') {
    if (data.prediction || data.gradcam?.available || quality.label !== 'Unacceptable' || quality.gate !== 'reupload') throw new Error('Invalid quality gate response.');
    return { ...data, result: null };
  }
  if ((data.status === 'completed') !== (data.gradcam?.available === true)) throw new Error('Invalid explanation status.');
  const p = data.prediction;
  const values = CLASS_KEYS.map(key => p?.probabilities?.[key]);
  if (!Number.isFinite(p?.confidence) || quality.gate !== 'proceed' || quality.label !== 'Acceptable' || !Number.isInteger(p?.class_id) || !RETINOPATHY_SEVERITIES[p.class_id] || p.class_name !== RETINOPATHY_SEVERITIES[p.class_id].label || values.some(v => !Number.isFinite(v) || v < 0 || v > 1) || Math.abs(values.reduce((a,b) => a+b, 0)-1) > 0.00001 || Math.abs(p.confidence-values[p.class_id]) > 0.00001 || p.confidence < Math.max(...values) || typeof p.is_calibrated !== 'boolean') throw new Error('Invalid severity response.');
  return { ...data, result: { predictedClass: p.class_id, confidence: p.confidence, probabilities: values, calibrated: p.is_calibrated,
    quality: quality.label.toLowerCase(), reliability: data.reliability, guidance: data.guidance, disclaimer: data.disclaimer,
    modelVersion: p.model_version, calibrationVersion: p.calibration_version, gradcam: data.gradcam,
    assessmentId: data.assessment_id, receivedAt: new Date().toISOString(), historical: false } };
}
export function displayHistoricalQuality(value) {
  const labels = { good: 'Good (historical three-class)', usable: 'Usable (historical three-class)', reject: 'Reject (historical three-class)', acceptable: 'Acceptable', unacceptable: 'Unacceptable' };
  return labels[value] || 'Not assessed';
}
export function normalizeRecord(record) {
  // Only stored facts: never run inference or reconstruct missing quality/guidance evidence.
  const artifacts = Object.fromEntries(CLASS_KEYS.map(key => [key, {}]));
  let original;
  for (const item of record.artifacts || []) {
    if (item.artifact_type === 'original') original = item.url;
    else if (CLASS_KEYS[item.severity_class]) artifacts[CLASS_KEYS[item.severity_class]][item.artifact_type === 'gradcam_overlay' ? 'overlay' : 'heatmap'] = item.url;
  }
  if (record.assessment_status !== 'completed') return null;
  const p = record.probabilities;
  if (!Number.isInteger(record.predicted_class) || !Number.isFinite(record.confidence) || !Array.isArray(p) || p.length !== 5 || p.some(v => !Number.isFinite(v) || v < 0 || v > 1) || Math.abs(p.reduce((a,b)=>a+b,0)-1)>0.00001 || !RETINOPATHY_SEVERITIES[record.predicted_class] || record.severity_label !== RETINOPATHY_SEVERITIES[record.predicted_class].label || Math.abs(record.confidence-p[record.predicted_class])>0.00001) throw new Error('Invalid saved result.');
  return { predictedClass: record.predicted_class, confidence: record.confidence, probabilities: p,
    calibrated: record.is_calibrated, quality: record.image_quality, qualityModelVersion: record.quality_model_version, modelVersion: record.model_version,
    reliability: { status: record.reliability_status, requires_review: record.reliability_status !== 'confident', reason: 'Stored reliability decision. Original explanatory text was not retained.' },
    guidance: { message: 'Original guidance text was not retained in this assessment.' },
    gradcam: { available: Object.values(artifacts).some(v => v.overlay || v.heatmap), artifacts, original },
    assessmentId: record.id, receivedAt: record.created_at, historical: true };
}
