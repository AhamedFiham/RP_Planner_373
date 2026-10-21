'use client';

import { useState, useCallback, useEffect } from 'react';
import { predictDiabetesRisk, fetchDiabetesHistory, fetchDiabetesModelInfo } from '@/lib/api';

export function useDiabetesPrediction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);

  const submitAssessment = useCallback(async (formData, token) => {
    setLoading(true);
    setError(null);
    try {
      const data = await predictDiabetesRisk(formData, token);
      setResult(data);
      // Prepend to current session history
      setHistory((prev) => [data, ...prev.filter((h) => h.id !== data.id)]);
      return data;
    } catch (err) {
      setError(err.message || 'An error occurred during assessment.');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async (token) => {
    setHistoryLoading(true);
    try {
      const past = await fetchDiabetesHistory(token);
      setHistory(past || []);
    } catch (err) {
      console.warn('Could not load history:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const loadModelInfo = useCallback(async () => {
    try {
      const info = await fetchDiabetesModelInfo();
      setModelInfo(info);
    } catch (err) {
      console.warn('Could not load model info:', err);
    }
  }, []);

  useEffect(() => {
    loadModelInfo();
    loadHistory();
  }, [loadModelInfo, loadHistory]);

  const resetAssessment = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    loading,
    error,
    result,
    history,
    historyLoading,
    modelInfo,
    submitAssessment,
    loadHistory,
    resetAssessment,
  };
}
