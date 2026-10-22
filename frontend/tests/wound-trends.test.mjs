import test from 'node:test';
import assert from 'node:assert/strict';
import { compareTissues, positionVisits, tissueSegments, visitDay } from '../lib/wound-trends.mjs';

const point = (visit_id, visit_date, value, status = 'ready') => ({ visit_id, visit_date, status, percentages: value === null ? null : { granulation: value } });

test('date spacing represents elapsed days, including leap days and single visits', () => {
  const result = positionVisits([point('a', '2026-10-01', 10), point('b', '2026-10-02', 20), point('c', '2026-10-11', 30)], 50, 700);
  assert.deepEqual(result.map(item => item.x), [50, 120, 750]);
  assert.equal(positionVisits([point('a', '2026-10-01', 10)], 50, 700)[0].x, 400);
  assert.equal(visitDay('2024-03-01') - visitDay('2024-02-28'), 2);
  assert.deepEqual(positionVisits([], 50, 700), []);
});

test('missing, zero-wound and invalid values break a line without inserting zeros', () => {
  const points = [point('a', '2026-10-01', 0), point('b', '2026-10-02', 30), point('c', '2026-10-03', null, 'pending'), point('d', '2026-10-04', 90), point('e', '2026-10-05', null, 'no_wound'), point('f', '2026-10-06', 101), point('g', '2026-10-07', 100)];
  const segments = tissueSegments(points, 'granulation');
  assert.deepEqual(segments.map(segment => segment.map(item => item.value)), [[0, 30], [90], [100]]);
  assert.equal(tissueSegments(points, 'unknown').length, 0);
});

test('composition comparison uses percentage points and reports gaps', () => {
  const points = [point('a', '2026-10-01', 20), point('b', '2026-10-02', null, 'failed'), point('c', '2026-10-07', 35)];
  const result = compareTissues(points, [{ key: 'granulation', label: 'Granulation' }]);
  assert.equal(result.changes[0].change, 15);
  assert.equal(result.skippedVisits, 1);
  assert.equal(result.first.visit_id, 'a');
  assert.equal(result.last.visit_id, 'c');
  assert.equal(compareTissues(points.slice(0, 2), []), null);
  assert.equal(compareTissues([], []), null);
});
