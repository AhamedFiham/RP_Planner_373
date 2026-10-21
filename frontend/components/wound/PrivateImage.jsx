'use client';

import { useEffect, useState } from 'react';
import { ImageOff } from 'lucide-react';
import { woundRequest } from '@/lib/wound-api';

export default function PrivateImage({ image, token, className = '', alt }) {
  const [source, setSource] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    setSource(''); setError('');
    woundRequest(`/images/${image.id}`, token, { blob: true, signal: controller.signal })
      .then(blob => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob); setSource(objectUrl);
      })
      .catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [image.id, token]);
  return source ? <img className={className} src={source} alt={alt || image.filename} /> :
    <div className={className} role="img" aria-label={error || 'Loading visit image'}><ImageOff size={24} /><span>{error ? 'Image unavailable' : 'Loading image…'}</span></div>;
}
