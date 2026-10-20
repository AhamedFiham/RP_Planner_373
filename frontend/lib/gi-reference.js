export const GI_CATEGORIES = ['Low', 'Medium', 'High'];

export const GI_EXPLANATIONS = {
  Low: 'Usually causes a slower rise in blood glucose.',
  Medium: 'May cause a moderate rise in blood glucose.',
  High: 'May cause a faster rise in blood glucose.',
};

export const giValueLabel = value => (typeof value === 'number' && Number.isFinite(value) ? `GI ${Math.round(value)}` : 'Not available yet');
export const giCategoryLabel = category => (GI_CATEGORIES.includes(category) ? category : null);
export const giExplanation = category => GI_EXPLANATIONS[category] || null;

export function validateGIRecords(data) {
  const fail = () => { throw new Error('The service returned an unexpected GI reference. Please try again.'); };
  if (!data || !Array.isArray(data.foods)) fail();
  for (const food of data.foods) {
    const gi = food.gi;
    if (!gi || !['matched', 'representative', 'candidate', 'needs_source'].includes(gi.mapping_status)) fail();
    if (gi.gi_value !== null && gi.gi_value !== undefined) {
      if (!Number.isFinite(gi.gi_value) || gi.gi_value <= 0) fail();
      if (!GI_CATEGORIES.includes(gi.gi_category)) fail();
    } else {
      if (gi.gi_category !== null && gi.gi_category !== undefined) fail();
    }
  }
  return data;
}
