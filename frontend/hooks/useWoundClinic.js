'use client';

import { useEffect, useRef, useState } from 'react';
import { woundRequest } from '@/lib/wound-api';

export default function useWoundClinic(token, modelId = '') {
  const [recordsToken, setRecordsToken] = useState(token);
  const tokenRef = useRef(token);
  tokenRef.current = token;
  const recordsCurrent = recordsToken === token;
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [wounds, setWounds] = useState([]);
  const [woundId, setWoundId] = useState('');
  const [visits, setVisits] = useState([]);
  const [progress, setProgress] = useState(null);
  const [progressRevision, setProgressRevision] = useState(0);
  const [progressError, setProgressError] = useState(null);
  const [progressLoading, setProgressLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState({ patients: true, wounds: false, visits: false });
  const [error, setError] = useState('');
  const refresh = () => setRevision(value => value + 1);
  const refreshProgress = () => setProgressRevision(value => value + 1);
  const progressScope = `${token || ''}:${woundId}:${modelId}`;

  useEffect(() => {
    // Hide records during the token-changing render, then start a fresh account selection.
    setPatients([]); setPatientId(''); setWounds([]); setWoundId(''); setVisits([]);
    setProgress(null); setProgressError(null); setProgressLoading(false); setError('');
    setLoading({ patients: Boolean(token), wounds: false, visits: false });
    setRecordsToken(token);
  }, [token]);

  useEffect(() => {
    setWounds([]); setWoundId(''); setVisits([]); setProgress(null);
  }, [token, patientId]);

  useEffect(() => { setVisits([]); setProgress(null); }, [token, woundId]);

  useEffect(() => {
    if (!token) {
      setPatients([]); setPatientId(''); setWounds([]); setWoundId(''); setVisits([]); setProgress(null);
      return;
    }
    const controller = new AbortController();
    setError(''); setLoading(value => ({ ...value, patients: true }));
    woundRequest('/patients', token, { signal: controller.signal })
      .then(items => {
        if (controller.signal.aborted) return;
        setPatients(items);
        setPatientId(current => items.some(item => item.id === current) ? current : items[0]?.id || '');
      })
      .catch(error => { if (!controller.signal.aborted && error.name !== 'AbortError') setError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(value => ({ ...value, patients: false })); });
    return () => controller.abort();
  }, [token, revision]);

  useEffect(() => {
    if (!recordsCurrent || !token || !patientId) { setWounds([]); setWoundId(''); setLoading(value => ({ ...value, wounds: false })); return; }
    const controller = new AbortController();
    setLoading(value => ({ ...value, wounds: true }));
    woundRequest(`/patients/${patientId}/wounds`, token, { signal: controller.signal })
      .then(items => {
        if (controller.signal.aborted) return;
        setWounds(items);
        setWoundId(current => items.some(item => item.id === current) ? current : items[0]?.id || '');
      })
      .catch(error => { if (!controller.signal.aborted && error.name !== 'AbortError') setError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(value => ({ ...value, wounds: false })); });
    return () => controller.abort();
  }, [token, patientId, revision, recordsCurrent]);

  useEffect(() => {
    if (!recordsCurrent || !token || !woundId) { setVisits([]); setProgress(null); setLoading(value => ({ ...value, visits: false })); return; }
    const controller = new AbortController();
    setLoading(value => ({ ...value, visits: true }));
    woundRequest(`/wounds/${woundId}/visits`, token, { signal: controller.signal })
      .then(items => { if (!controller.signal.aborted) setVisits(items); })
      .catch(error => { if (!controller.signal.aborted && error.name !== 'AbortError') setError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(value => ({ ...value, visits: false })); });
    return () => controller.abort();
  }, [token, woundId, revision, recordsCurrent]);

  useEffect(() => {
    if (!recordsCurrent || !token || !woundId) { setProgress(null); setProgressLoading(false); return; }
    const controller = new AbortController();
    const scope = progressScope;
    setProgress(null); setProgressError(null); setProgressLoading(true);
    const query = modelId ? `?model_id=${encodeURIComponent(modelId)}` : '';
    woundRequest(`/wounds/${woundId}/progress${query}`, token, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setProgress({ data, scope }); })
      .catch(error => { if (!controller.signal.aborted && error.name !== 'AbortError') setProgressError({ message: error.message, scope }); })
      .finally(() => { if (!controller.signal.aborted) setProgressLoading(false); });
    return () => controller.abort();
  }, [token, woundId, modelId, revision, progressRevision, progressScope, recordsCurrent]);

  function requireCurrentSession(requestToken) {
    if (requestToken !== tokenRef.current) throw new Error('Your session changed. Please try again.');
  }

  function selectPatient(id) {
    if (id === patientId) return;
    setPatientId(id); setWoundId(''); setWounds([]); setVisits([]); setProgress(null); setError('');
  }
  function selectWound(id) {
    if (id === woundId) return;
    setWoundId(id); setVisits([]); setProgress(null); setError('');
  }
  async function createPatient(body) {
    const requestToken = token;
    const result = await woundRequest('/patients', token, { method: 'POST', body });
    requireCurrentSession(requestToken);
    setPatients(items => [...items, result]); selectPatient(result.id); refresh(); return result;
  }
  async function createWound(body) {
    const requestToken = token;
    const result = await woundRequest(`/patients/${patientId}/wounds`, token, { method: 'POST', body });
    requireCurrentSession(requestToken);
    setWounds(items => [...items, result]); selectWound(result.id); refresh(); return result;
  }
  async function createVisit(body) {
    const requestToken = token;
    const result = await woundRequest(`/wounds/${woundId}/visits`, token, { method: 'POST', body });
    requireCurrentSession(requestToken);
    refresh(); return result;
  }
  async function changeStatus(status) {
    const requestToken = token;
    await woundRequest(`/wounds/${woundId}`, token, { method: 'PATCH', body: { status } });
    requireCurrentSession(requestToken);
    refresh();
  }
  async function selectProgressImage(visitId, imageId) {
    const requestToken = token;
    await woundRequest(`/visits/${visitId}/progress-image`, token, { method: 'PATCH', body: { image_id: imageId } });
    requireCurrentSession(requestToken);
    refreshProgress();
  }
  return {
    patients: recordsCurrent ? patients : [], wounds: recordsCurrent ? wounds : [], visits: recordsCurrent ? visits : [],
    patientId: recordsCurrent ? patientId : '', woundId: recordsCurrent ? woundId : '',
    loading: recordsCurrent ? loading : { patients: Boolean(token), wounds: false, visits: false },
    error: recordsCurrent ? error : '', refresh,
    progress: recordsCurrent && progress?.scope === progressScope ? progress.data : null,
    progressError: recordsCurrent && progressError?.scope === progressScope ? progressError.message : '',
    progressLoading: recordsCurrent && (progressLoading || Boolean(token && woundId && progress?.scope !== progressScope && progressError?.scope !== progressScope)),
    refreshProgress, selectProgressImage,
    patient: recordsCurrent ? patients.find(item => item.id === patientId) : undefined,
    wound: recordsCurrent ? wounds.find(item => item.id === woundId) : undefined,
    selectPatient, selectWound, createPatient, createWound, createVisit, changeStatus,
  };
}
