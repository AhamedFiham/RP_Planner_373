'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Database,
  FileText,
  History,
  Info,
  Layers,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserCheck
} from 'lucide-react';
import { useAuth } from '@/components/auth-provider';
import { useDiabetesPrediction } from '@/hooks/useDiabetesPrediction';
import DiabetesForm from '@/components/diabetes/DiabetesForm';
import RiskResult from '@/components/diabetes/RiskResult';
import RiskHistory from '@/components/diabetes/RiskHistory';

export default function DiabetesRiskPredictionPage() {
  const { token, user } = useAuth() || {};
  const {
    loading,
    error,
    result,
    history,
    historyLoading,
    modelInfo,
    submitAssessment,
    resetAssessment,
  } = useDiabetesPrediction();

  const [activeTab, setActiveTab] = useState('assessment'); // 'assessment' | 'history' | 'model_info'
  const [selectedHistoricalResult, setSelectedHistoricalResult] = useState(null);

  const handleSubmit = async (formData) => {
    try {
      setSelectedHistoricalResult(null);
      await submitAssessment(formData, token);
      setActiveTab('assessment');
    } catch (_) {
      // Error is tracked in hook
    }
  };

  const handleSelectHistorical = (pastRecord) => {
    setSelectedHistoricalResult(pastRecord);
    setActiveTab('assessment');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const activeDisplayResult = selectedHistoricalResult || result;

  return (
    <div className="min-h-screen bg-slate-50/70 text-slate-800">
      {/* Top Clinical Navigation Bar */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-700 bg-slate-100 hover:bg-slate-200/80 px-3 py-1.5 rounded-lg transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Portal Dashboard</span>
            </Link>

            <div className="h-5 w-[1px] bg-slate-200 hidden sm:block"></div>

            <div className="flex items-center gap-2">
              <span className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shadow-sm">
                R1
              </span>
              <div>
                <h1 className="text-sm font-bold text-slate-900 leading-tight m-0">
                  Explainable Diabetes Risk Prediction
                </h1>
                <p className="text-[11px] text-slate-500 m-0">
                  Smart Diabetes Prediction & Personalized Care System
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              ML Service Online
            </span>
            {user?.name && (
              <div className="hidden md:flex items-center gap-2 pl-3 border-l border-slate-200 text-xs">
                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center text-[10px]">
                  {user.name.charAt(0)}
                </div>
                <span className="font-semibold text-slate-700">{user.name}</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Navigation Tabs Bar */}
        <div className="flex items-center gap-2 bg-slate-200/60 p-1 rounded-2xl w-fit border border-slate-200">
          <button
            type="button"
            onClick={() => setActiveTab('assessment')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'assessment'
                ? 'bg-white text-blue-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Stethoscope className="w-4 h-4 text-blue-600" />
            <span>Clinical Assessment & SHAP</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('history')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'history'
                ? 'bg-white text-blue-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <History className="w-4 h-4 text-indigo-600" />
            <span>Assessment Logs</span>
            <span className="px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700 font-mono text-[10px]">
              {history?.length || 0}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('model_info')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'model_info'
                ? 'bg-white text-blue-900 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <BarChart3 className="w-4 h-4 text-emerald-600" />
            <span>Model Validation & Metrics</span>
          </button>
        </div>

        {/* TAB 1: ASSESSMENT & RESULTS */}
        {activeTab === 'assessment' && (
          <div className="space-y-6">
            {activeDisplayResult ? (
              <div className="space-y-4">
                {selectedHistoricalResult && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-blue-900 text-xs flex items-center justify-between shadow-xs">
                    <span className="flex items-center gap-2">
                      <Info className="w-4 h-4 text-blue-600 shrink-0" />
                      <span>
                        Viewing archived evaluation from{' '}
                        <strong>{new Date(selectedHistoricalResult.timestamp).toLocaleString()}</strong>
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={() => setSelectedHistoricalResult(null)}
                      className="px-3 py-1 bg-white text-blue-800 rounded-lg border border-blue-200 text-xs font-bold hover:bg-blue-100/50 transition cursor-pointer"
                    >
                      Return to Active Test
                    </button>
                  </div>
                )}

                <RiskResult
                  data={activeDisplayResult}
                  onReset={() => {
                    resetAssessment();
                    setSelectedHistoricalResult(null);
                  }}
                />
              </div>
            ) : (
              <div>
                <DiabetesForm onSubmit={handleSubmit} loading={loading} error={error} />
              </div>
            )}
          </div>
        )}

        {/* TAB 2: LOGS & HISTORY */}
        {activeTab === 'history' && (
          <div>
            <RiskHistory
              history={history}
              loading={historyLoading}
              onSelectAssessment={handleSelectHistorical}
            />
          </div>
        )}

        {/* TAB 3: MODEL ARCHITECTURE & METRICS */}
        {activeTab === 'model_info' && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-md p-6 md:p-8 space-y-6">
            <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-100 gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Database className="w-4 h-4 text-blue-600" />
                  <h2 className="text-xl font-bold text-slate-900 m-0">
                    Machine Learning Validation & Provenance
                  </h2>
                </div>
                <p className="text-xs text-slate-500 m-0">
                  Benchmarking of candidate algorithms on 20,199 untouched stratified test patients.
                </p>
              </div>

              <div className="text-xs px-3 py-1.5 bg-blue-50 text-blue-900 border border-blue-200 rounded-xl font-mono">
                Optimal Decision Threshold: <strong>0.40</strong> (High Sensitivity)
              </div>
            </div>

            {/* Model Comparison Table */}
            {modelInfo?.metrics?.models_evaluated ? (
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[11px] border-b border-slate-200">
                      <th className="py-3 px-4">Architecture</th>
                      <th className="py-3 px-4">ROC-AUC</th>
                      <th className="py-3 px-4">PR-AUC</th>
                      <th className="py-3 px-4">Sensitivity (Recall)</th>
                      <th className="py-3 px-4">Specificity</th>
                      <th className="py-3 px-4">F1-Score</th>
                      <th className="py-3 px-4">False Negatives</th>
                      <th className="py-3 px-4 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.entries(modelInfo.metrics.models_evaluated).map(([name, m]) => {
                      const isSelected = name === modelInfo.metrics.selected_model;

                      return (
                        <tr
                          key={name}
                          className={isSelected ? 'bg-blue-50/60 font-semibold' : 'hover:bg-slate-50/50'}
                        >
                          <td className="py-3.5 px-4 text-slate-900 font-bold">
                            {name}
                          </td>
                          <td className="py-3.5 px-4 font-mono font-bold text-slate-800">
                            {(m.roc_auc * 100).toFixed(2)}%
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-700">
                            {(m.pr_auc * 100).toFixed(2)}%
                          </td>
                          <td className="py-3.5 px-4 font-mono text-emerald-700 font-extrabold text-sm">
                            {(m.recall_sensitivity * 100).toFixed(2)}%
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-700">
                            {(m.specificity * 100).toFixed(2)}%
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-700">
                            {(m.f1_score * 100).toFixed(2)}%
                          </td>
                          <td className="py-3.5 px-4 font-mono text-rose-700">
                            {m.confusion_matrix?.false_negative} / {m.confusion_matrix?.false_negative + m.confusion_matrix?.true_positive}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            {isSelected ? (
                              <span className="px-2.5 py-1 rounded-full bg-blue-600 text-white text-[10px] font-extrabold uppercase tracking-wider">
                                Selected Model
                              </span>
                            ) : (
                              <span className="text-slate-400 text-[11px]">Evaluated</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-500">
                Loading model validation data...
              </div>
            )}

            {/* Threshold Analysis Card */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-100">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-700 mb-1 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-blue-600" />
                  Dataset Provenance
                </h4>
                <p className="text-xs text-slate-600 m-0 leading-relaxed">
                  Trained on 100,992 clinical records (92,407 non-diabetic, 8,585 diabetic). Evaluated on 20,199 test partition with zero data leakage.
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-700 mb-1 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  Exact SHAP Attribution
                </h4>
                <p className="text-xs text-slate-600 m-0 leading-relaxed">
                  Employs tree-based exact SHAP algorithms in true probability space, satisfying mathematical additivity without log-odds distortion.
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <h4 className="font-bold text-xs uppercase tracking-wider text-slate-700 mb-1 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  Clinical Separation
                </h4>
                <p className="text-xs text-slate-600 m-0 leading-relaxed">
                  WHO 2006/2011/2019 and ADA 2024 diagnostic rules operate independently of the ML model, guaranteeing clinical flags are never suppressed.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
