'use client';

import { useEffect, useState } from 'react';
import { ImageOff } from 'lucide-react';
import { woundRequest } from '@/lib/wound-api';

export default function PrivateImage({ image, token, resourcePath, className = '', alt }) {
  const resourceKey = `${token || ''}\0${resourcePath || image.id}`;
  const [loaded, setLoaded] = useState(null);
  const [failure, setFailure] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    setLoaded(null); setFailure(null);
    woundRequest(resourcePath || `/images/${image.id}`, token, { blob: true, signal: controller.signal })
      .then(blob => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob); setLoaded({ key: resourceKey, url: objectUrl });
      })
      .catch(error => { if (!controller.signal.aborted && error.name !== 'AbortError') setFailure({ key: resourceKey, message: error.message }); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [image.id, token, resourcePath, resourceKey]);
  const source = loaded?.key === resourceKey ? loaded.url : '';
  const error = failure?.key === resourceKey ? failure.message : '';
  return source ? <img className={className} src={source} alt={alt || image.filename} /> :
    <div className={className} role="img" aria-label={error || 'Loading visit image'}><ImageOff size={24} /><span>{error ? 'Image unavailable' : 'Loading image…'}</span></div>;
}
