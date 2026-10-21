'use client';

import { useEffect, useState } from 'react';
import { woundRequest } from '@/lib/wound-api';

export default function useWoundClinic(token) {
  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [wounds, setWounds] = useState([]);
  const [woundId, setWoundId] = useState('');
  const [visits, setVisits] = useState([]);
  const [progress, setProgress] = useState(null);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState({ patients: true, wounds: false, visits: false });
  const [error, setError] = useState('');
  const refresh = () => setRevision(value => value + 1);

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
    if (!token || !patientId) { setWounds([]); setWoundId(''); setLoading(value => ({ ...value, wounds: false })); return; }
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
  }, [token, patientId, revision]);

  useEffect(() => {
    if (!token || !woundId) { setVisits([]); setProgress(null); setLoading(value => ({ ...value, visits: false })); return; }
    const controller = new AbortController();
    setLoading(value => ({ ...value, visits: true }));
    Promise.all([
      woundRequest(`/wounds/${woundId}/visits`, token, { signal: controller.signal }),
      woundRequest(`/wounds/${woundId}/progress`, token, { signal: controller.signal }),
    ]).then(([items, chart]) => { if (!controller.signal.aborted) { setVisits(items); setProgress(chart); } })
      .catch(error => { if (!controller.signal.aborted && error.name !== 'AbortError') setError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(value => ({ ...value, visits: false })); });
    return () => controller.abort();
  }, [token, woundId, revision]);

  function selectPatient(id) {
    if (id === patientId) return;
    setPatientId(id); setWoundId(''); setWounds([]); setVisits([]); setProgress(null); setError('');
  }
  function selectWound(id) {
    if (id === woundId) return;
    setWoundId(id); setVisits([]); setProgress(null); setError('');
  }
  async function createPatient(body) {
    const result = await woundRequest('/patients', token, { method: 'POST', body });
    setPatients(items => [...items, result]); selectPatient(result.id); refresh(); return result;
  }
  async function createWound(body) {
    const result = await woundRequest(`/patients/${patientId}/wounds`, token, { method: 'POST', body });
    setWounds(items => [...items, result]); selectWound(result.id); refresh(); return result;
  }
  async function createVisit(body) {
    const result = await woundRequest(`/wounds/${woundId}/visits`, token, { method: 'POST', body });
    refresh(); return result;
  }
  async function changeStatus(status) {
    await woundRequest(`/wounds/${woundId}`, token, { method: 'PATCH', body: { status } });
    refresh();
  }
  return {
    patients, wounds, visits, progress, patientId, woundId, loading, error, refresh,
    patient: patients.find(item => item.id === patientId), wound: wounds.find(item => item.id === woundId),
    selectPatient, selectWound, createPatient, createWound, createVisit, changeStatus,
  };
}
