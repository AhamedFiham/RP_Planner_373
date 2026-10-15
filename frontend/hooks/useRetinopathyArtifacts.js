'use client';
import { useEffect, useState } from 'react';
export default function useRetinopathyArtifacts(api, gradcam) {
  const [state, setState] = useState({ source: null, urls: {}, loading: false, error: '' });
  useEffect(() => {
    const controller = new AbortController(); const urls = {}; const created = []; let active = true;
    const paths = [...new Set([gradcam?.original, ...Object.values(gradcam?.artifacts || {}).flatMap(v => [v.heatmap, v.overlay])].filter(Boolean))];
    if (!paths.length) return;
    setState({ source: gradcam, urls: {}, loading: true, error: '' });
    let failed = false;
    // Sequential requests bound image memory/network work; each successful image appears immediately.
    (async () => {
      for (const path of paths) {
        try {
          const blob = await api.artifact(path, controller.signal);
          if (!active) return;
          const url = URL.createObjectURL(blob); created.push(url); urls[path] = url;
          setState({ source: gradcam, urls: { ...urls }, loading: true, error: failed ? 'Some protected images are unavailable.' : '' });
        } catch { if (!active) return; failed = true; }
      }
      if (active) setState({ source: gradcam, urls, loading: false, error: failed ? 'Some protected images could not be loaded or have expired.' : '' });
    })();
    return () => { active = false; controller.abort(); created.forEach(url => URL.revokeObjectURL(url)); };
  }, [api, gradcam]);
  return state.source === gradcam ? state : { urls: {}, loading: false, error: '' };
}
