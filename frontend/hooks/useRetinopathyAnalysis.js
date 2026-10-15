'use client';
import { useEffect, useRef, useState } from 'react';
import { validateRetinalFile } from '@/lib/retinopathy/constants';
import { normalizeAnalysis } from '@/lib/retinopathy/contract';

export default function useRetinopathyAnalysis(api) {
  const [status, setStatus] = useState('idle');
  const [selectedImage, setSelectedImage] = useState(null);
  const [error, setError] = useState('');
  const [quality, setQuality] = useState(null);
  const [result, setResult] = useState(null);
  const [historyRevision, setHistoryRevision] = useState(0);
  const pending = useRef(null);
  const revision = useRef(0);
  const imageUrl = useRef('');
  function cancel() { revision.current++; pending.current?.abort(); pending.current = null; }
  useEffect(() => () => { revision.current++; pending.current?.abort(); if (imageUrl.current) URL.revokeObjectURL(imageUrl.current); }, []);
  function reset() {
    cancel(); if (imageUrl.current) URL.revokeObjectURL(imageUrl.current); imageUrl.current = '';
    setSelectedImage(null); setQuality(null); setResult(null); setError(''); setStatus('idle');
  }
  function selectImage(file, selectionError = '') {
    reset(); const problem = selectionError || validateRetinalFile(file);
    if (problem) { setError(problem); setStatus('failed'); return; }
    const version = revision.current; const url = URL.createObjectURL(file); imageUrl.current = url;
    const preview = new Image();
    preview.onload = () => { if (version !== revision.current) return; setSelectedImage({ file, url }); setStatus('image_selected'); };
    preview.onerror = () => { if (version !== revision.current) return; URL.revokeObjectURL(url); imageUrl.current = ''; setError('This image could not be opened. Please select a readable JPG or PNG.'); setStatus('failed'); };
    preview.src = url;
  }
  async function analyze() {
    if (!selectedImage || pending.current) return;
    const controller = new AbortController(); pending.current = controller; const version = ++revision.current;
    setError(''); setQuality(null); setResult(null); setStatus('analyzing');
    const timeout = setTimeout(() => controller.abort('timeout'), 150000);
    try {
      const response = normalizeAnalysis(await api.analyze(selectedImage.file, controller.signal));
      if (version !== revision.current) return;
      setQuality(response.image_quality); setResult(response.result);
      setStatus(response.status === 'quality_rejected' ? 'quality_rejected' : response.result.reliability?.requires_review ? 'uncertain' : 'completed');
      if (response.assessment_id) setHistoryRevision(v => v+1);
    } catch (failure) {
      if (version !== revision.current) return;
      setResult(null); setQuality(null);
      setStatus(failure.code?.includes('model') || failure.code === 'configuration_unavailable' ? 'model_unavailable' : 'failed');
      setError(controller.signal.aborted ? 'Analysis was cancelled or timed out. The server may still finish processing; check history before retrying.' : failure.status !== undefined ? failure.message : 'The service returned an invalid analysis response.');
      if (failure.assessmentId || controller.signal.aborted) setHistoryRevision(v => v+1);
    } finally { clearTimeout(timeout); if (version === revision.current) pending.current = null; }
  }
  function clearDeleted(id) { setResult(current => current?.assessmentId === id ? null : current); }
  return { clearDeleted, status, selectedImage, error, quality, result, selectImage, reset, analyze, historyRevision };
}
