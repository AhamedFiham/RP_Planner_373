'use client';
import { useEffect, useRef, useState } from 'react';
import { detectMeal } from '@/lib/api';
import { validateMealFile } from '@/lib/diet-detection';

export default function useDietDetection() {
  const [selectedFile, setFile] = useState(null);
  const [previewUrl, setPreview] = useState(null);
  const [dimensions, setDimensions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const url = useRef(null);
  const controller = useRef(null);
  const generation = useRef(0);
  const busy = useRef(false);
  function release() { controller.current?.abort(); if (url.current) URL.revokeObjectURL(url.current); url.current = null; busy.current = false; }
  useEffect(() => () => { generation.current++; release(); }, []);
  function resetDetection() {
    generation.current++; release(); setFile(null); setPreview(null); setDimensions(null); setResult(null); setError(null); setLoading(false); setPreparing(false);
  }
  async function selectFile(file) {
    resetDetection();
    const message = validateMealFile(file);
    if (message) { setError(message); return; }
    const version = generation.current;
    const nextUrl = URL.createObjectURL(file); url.current = nextUrl; setPreparing(true);
    const image = new Image();
    image.onload = () => {
      if (version !== generation.current) return;
      if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth * image.naturalHeight > 20_000_000) {
        release(); setPreparing(false); setError('Choose an image with valid dimensions under 20 million pixels.'); return;
      }
      setFile(file); setPreview(nextUrl); setDimensions({ width: image.naturalWidth, height: image.naturalHeight }); setPreparing(false);
    };
    image.onerror = () => { if (version === generation.current) { release(); setPreparing(false); setError('This image could not be opened. Choose another JPG, PNG or WebP image.'); } };
    image.src = nextUrl;
  }
  async function analyzeMeal() {
    if (!selectedFile || busy.current) return;
    busy.current = true; const version = generation.current;
    setLoading(true); setError(null); setResult(null);
    const request = new AbortController(); controller.current = request;
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; request.abort(); }, 60000);
    try {
      const data = await detectMeal(selectedFile, { signal: request.signal });
      if (version === generation.current) setResult(data);
    } catch (failure) {
      if (version === generation.current && (failure.name !== 'AbortError' || timedOut)) setError(timedOut ? 'Analysis took too long. Please try again.' : failure.message);
    } finally {
      clearTimeout(timeout);
      if (version === generation.current) { setLoading(false); busy.current = false; }
    }
  }
  return { selectedFile, previewUrl, dimensions, loading, preparing, error, result, selectFile, analyzeMeal, resetDetection };
}
