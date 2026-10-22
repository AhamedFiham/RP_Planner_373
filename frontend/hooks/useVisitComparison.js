'use client';

import { useEffect, useRef, useState } from 'react';
import { woundRequest } from '@/lib/wound-api';
import { prepareVisitComparison } from '@/lib/visit-comparison.mjs';

export default function useVisitComparison({ token, woundId, modelId, progress, onComplete }) {
  const scope = `${token || ''}\0${woundId || ''}\0${modelId || ''}`;
  const currentScope = useRef(scope);
  currentScope.current = scope;
  const mounted = useRef(true);
  const running = useRef(null);
  const [state, setState] = useState(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);

  async function analyzeVisits({ visitIds }) {
    if (running.current?.scope === scope) return;
    if (!token || !woundId || !modelId || progress?.model_id !== modelId) throw new Error('Load the selected model’s visit results before analyzing.');
    const operation = { scope };
    running.current = operation;
    const isCurrent = () => mounted.current && currentScope.current === scope && running.current === operation;
    const update = value => { if (isCurrent()) setState({ scope, ...value }); };
    update({ busy: true, message: 'Preparing the selected visit images…' });
    try {
      const result = await prepareVisitComparison({
        points: progress.points, visitIds, modelId, isCurrent,
        analyze: (imageId, stage, selectedModel) => woundRequest(`/images/${imageId}/analysis`, token, { method: 'POST', body: { stage, model_id: selectedModel } }),
        onProgress: ({ visitDate, stage }) => update({ busy: true, message: `${visitDate}: running ${stage === 'wound_segmentation' ? 'wound' : 'tissue'} segmentation…` }),
      });
      if (!isCurrent()) return;
      if (result.failed.length) {
        update({ busy: false, message: `${result.completed + result.reused} visits prepared. ${result.failed.map(item => `${item.visitDate}: ${item.message}`).join(' ')}` });
      } else {
        update({ busy: false, message: 'Saved masks are ready. Refreshing tissue proportions…' });
      }
      onComplete?.();
    } catch (error) {
      if (!isCurrent() || error.name === 'AbortError') return;
      update({ busy: false, message: error.message });
      onComplete?.();
    } finally {
      if (running.current === operation) running.current = null;
    }
  }

  return { analyzeVisits, analyzing: state?.scope === scope && state.busy, analysisMessage: state?.scope === scope ? state.message : '' };
}
