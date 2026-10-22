import test from 'node:test';
import assert from 'node:assert/strict';
import { prepareVisitComparison } from '../lib/visit-comparison.mjs';

const point = (id, status = 'pending') => ({ visit_id: id, image_id: `photo-${id}`, visit_date: `2026-10-${id}`, status });

test('prepares selected photos with wound before tissue and the same model', async () => {
  const calls = [];
  const result = await prepareVisitComparison({ points: [point('01'), point('07')], visitIds: ['01', '07'], modelId: 'unet', analyze: async (...args) => { calls.push(args); return { status: 'completed' }; } });
  assert.deepEqual(calls, [['photo-01', 'wound_segmentation', 'unet'], ['photo-01', 'tissue_segmentation', 'unet'], ['photo-07', 'wound_segmentation', 'unet'], ['photo-07', 'tissue_segmentation', 'unet']]);
  assert.equal(result.completed, 2);
});

test('reuses ready and valid no-wound results and deduplicates visits', async () => {
  const result = await prepareVisitComparison({ points: [point('01', 'ready'), { ...point('07', 'no_wound'), analysis: {} }], visitIds: ['01', '01', '07'], modelId: 'unet', analyze: () => { throw new Error('Must reuse existing results'); } });
  assert.equal(result.reused, 2);
  assert.deepEqual(result.failed, []);
});

test('failed wound segmentation does not run dependent tissue but allows the other visit', async () => {
  const calls = [];
  const result = await prepareVisitComparison({ points: [point('01'), point('07')], visitIds: ['01', '07'], modelId: 'unet', analyze: async (image, stage) => { calls.push([image, stage]); return image === 'photo-01' ? { status: 'failed', error: 'Wound inference failed' } : { status: 'completed' }; } });
  assert.deepEqual(calls, [['photo-01', 'wound_segmentation'], ['photo-07', 'wound_segmentation'], ['photo-07', 'tissue_segmentation']]);
  assert.equal(result.completed, 1);
  assert.equal(result.failed[0].message, 'Wound inference failed');
});

test('changing account, wound or model stops dependent requests', async () => {
  let active = true;
  const calls = [];
  await assert.rejects(prepareVisitComparison({ points: [point('01')], visitIds: ['01'], modelId: 'unet', isCurrent: () => active, analyze: async (...args) => { calls.push(args); active = false; return { status: 'completed' }; } }), { name: 'AbortError' });
  assert.equal(calls.length, 1);
});

test('unknown or missing-photo visits cannot produce analysis requests', async () => {
  for (const visitIds of [[], ['missing'], ['01', '02', '03']]) {
    await assert.rejects(prepareVisitComparison({ points: [point('01')], visitIds, modelId: 'unet', analyze: () => { throw new Error('No request should run'); } }));
  }
});
