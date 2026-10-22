const DAY = 86_400_000;

export function visitDay(value) {
  return Date.parse(`${value}T00:00:00Z`) / DAY;
}

export function positionVisits(points, left, width) {
  if (!points.length) return [];
  const days = points.map(point => visitDay(point.visit_date));
  const first = Math.min(...days);
  const span = Math.max(...days) - first;
  return points.map((point, index) => ({
    ...point,
    x: span ? left + ((days[index] - first) / span) * width : left + width / 2,
  }));
}

// A missing result breaks the line; it must never become a zero or interpolation.
export function tissueSegments(points, key) {
  const segments = [];
  let current = [];
  for (const point of points) {
    const value = point.status === 'ready' ? point.percentages?.[key] : null;
    if (Number.isFinite(value) && value >= 0 && value <= 100) {
      current.push({ ...point, value });
    } else if (current.length) {
      segments.push(current);
      current = [];
    }
  }
  if (current.length) segments.push(current);
  return segments;
}

export function compareTissues(points, tissues) {
  const ready = points.filter(point => point.status === 'ready' && point.percentages);
  if (ready.length < 2) return null;
  const first = ready[0];
  const last = ready.at(-1);
  return {
    first, last,
    changes: tissues.map(tissue => ({
      ...tissue,
      before: first.percentages[tissue.key],
      after: last.percentages[tissue.key],
      change: last.percentages[tissue.key] - first.percentages[tissue.key],
    })),
    skippedVisits: points.slice(points.indexOf(first), points.indexOf(last) + 1).filter(point => point.status !== 'ready').length,
  };
}
