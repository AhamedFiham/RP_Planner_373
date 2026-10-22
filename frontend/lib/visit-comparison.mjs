function requireActive(isCurrent) {
  if (!isCurrent()) {
    const error = new Error('The selected wound or model changed. Reload the comparison to continue.');
    error.name = 'AbortError';
    throw error;
  }
}

// Reuse saved results; dependent stages always run in order for each selected image.
export async function prepareVisitComparison({ points, visitIds, modelId, analyze, isCurrent = () => true, onProgress = () => {} }) {
  const ids = [...new Set(visitIds)];
  if (!modelId || !ids.length || ids.length > 2) throw new Error('Choose a model and up to two visits to analyze.');
  const selected = ids.map(id => points.find(point => point.visit_id === id));
  if (selected.some(point => !point?.image_id)) throw new Error('Each selected visit needs a wound photo.');
  const result = { completed: 0, reused: 0, failed: [] };
  for (const point of selected) {
    requireActive(isCurrent);
    if (point.status === 'ready' || (point.status === 'no_wound' && point.analysis)) {
      result.reused += 1;
      continue;
    }
    try {
      for (const stage of ['wound_segmentation', 'tissue_segmentation']) {
        requireActive(isCurrent);
        onProgress({ visitDate: point.visit_date, stage });
        const run = await analyze(point.image_id, stage, modelId);
        requireActive(isCurrent);
        if (run.status !== 'completed') throw new Error(run.error || 'The segmentation did not complete. Retry this visit.');
      }
      result.completed += 1;
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      result.failed.push({ visitDate: point.visit_date, message: error.message });
    }
  }
  return result;
}
