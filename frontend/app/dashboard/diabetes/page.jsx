'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  FileText,
  History,
  Info,
  Layers,
  PlusCircle,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  TrendingDown,
  TrendingUp,
  UserCheck
} from 'lucide-react';
import DashboardShell from '@/components/dashboard/DashboardShell';
import { useAuth } from '@/components/auth-provider';
import { fetchDiabetesHistory } from '@/lib/api';

export default function DiabetesDashboardPage() {
  const { token, user } = useAuth() || {};
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const past = await fetchDiabetesHistory(token, 10);
        setHistory(past || []);
      } catch (err) {
        console.warn('History load error:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [token]);

  const latestAssessment = history.length > 0 ? history[0] : null;
  const isPositive = latestAssessment?.prediction?.label === 'positive';
  const latestProb = latestAssessment ? Math.round((latestAssessment.prediction?.probability || 0) * 100) : null;

  return (
    <DashboardShell title="Diabetes Risk Assessment Workspace" hideSidebar>
      <div className="max-w-6xl mx-auto space-y-8 py-4">
        {/* Hero Welcome Banner */}
        <section className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
          <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-radial from-blue-500/10 to-transparent pointer-events-none"></div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
            <div className="space-y-2 max-w-2xl">
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-300 border border-blue-400/30 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                  Explainable AI & WHO Clinical Engine
                </span>
                <span className="text-xs text-slate-400 font-mono">Component 1</span>
              </div>

              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white m-0">
                Diabetes Risk Assessment Workspace
              </h1>

              <p className="text-slate-300 text-xs md:text-sm m-0 leading-relaxed">
                Welcome back{user?.name ? `, ${user.name}` : ''}. Evaluate clinical biomarkers, generate patient-specific SHAP explainability insights, and receive personalized diabetes prevention guidance.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/diabetes"
                className="px-6 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-sm rounded-xl shadow-lg shadow-blue-900/40 hover:shadow-xl transition flex items-center gap-2 shrink-0"
              >
                <span>Start Risk Assessment</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </section>

        {/* Dashboard Grid Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Card 1: Latest Assessment Status */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
                <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                  <Activity className="w-4 h-4 text-blue-600" />
                  <span>Latest Evaluation</span>
                </div>
                {latestAssessment && (
                  <span className="text-[11px] text-slate-400 font-mono">
                    {new Date(latestAssessment.timestamp).toLocaleDateString()}
                  </span>
                )}
              </div>

              {loading ? (
                <div className="py-8 text-center text-xs text-slate-400">Loading evaluation status...</div>
              ) : latestAssessment ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Estimated Risk
                      </div>
                      <div className="text-2xl font-black text-slate-900 font-mono">
                        {latestProb}%
                      </div>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                        isPositive
                          ? 'bg-rose-50 text-rose-700 border border-rose-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}
                    >
                      {latestAssessment.prediction?.label}
                    </span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-500">WHO Status:</span>
                      <strong className="capitalize">{latestAssessment.clinical_assessment?.status?.replace('_', ' ')}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">HbA1c Tested:</span>
                      <strong className="font-mono">{latestAssessment.input?.HbA1c_level || latestAssessment.input?.hba1c_level}%</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Glucose:</span>
                      <strong className="font-mono">{latestAssessment.input?.blood_glucose_level} mg/dL</strong>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-slate-500 space-y-2">
                  <p className="m-0">No completed assessments recorded yet.</p>
                  <p className="text-[11px] text-slate-400 m-0">
                    Complete your first clinical assessment to start tracking your metabolic risk.
                  </p>
                </div>
              )}
            </div>

            <div className="pt-4 mt-4 border-t border-slate-100">
              <Link
                href="/diabetes"
                className="text-xs font-bold text-blue-700 hover:text-blue-900 flex items-center justify-between"
              >
                <span>{latestAssessment ? 'Open Full Workspace' : 'Launch Assessment'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card 2: Clinical Preparation Steps */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 pb-3 mb-3 border-b border-slate-100 text-slate-800 font-bold text-sm">
                <FileText className="w-4 h-4 text-emerald-600" />
                <span>Assessment Preparation</span>
              </div>

              <ul className="space-y-3 text-xs text-slate-700">
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                    1
                  </span>
                  <div>
                    <strong className="text-slate-900">Have Your Glycemic Tests Ready:</strong>
                    <p className="text-slate-500 text-[11px] m-0">Recent laboratory HbA1c and fasting or random blood glucose values.</p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                    2
                  </span>
                  <div>
                    <strong className="text-slate-900">Review Health History:</strong>
                    <p className="text-slate-500 text-[11px] m-0">Current BMI, history of hypertension, cardiovascular disease, and smoking status.</p>
                  </div>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center text-[10px] shrink-0 mt-0.5">
                    3
                  </span>
                  <div>
                    <strong className="text-slate-900">Share with Clinician:</strong>
                    <p className="text-slate-500 text-[11px] m-0">Discuss results and SHAP insights with your licensed physician for care planning.</p>
                  </div>
                </li>
              </ul>
            </div>

            <div className="pt-4 mt-4 border-t border-slate-100">
              <span className="text-[11px] text-slate-400">Aligned with WHO 2019 / ADA 2024 standards</span>
            </div>
          </div>

          {/* Card 3: System Overview & Research Specs */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-md flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 pb-3 mb-3 border-b border-slate-100 text-slate-800 font-bold text-sm">
                <ShieldCheck className="w-4 h-4 text-purple-600" />
                <span>Explainable AI Verification</span>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="font-bold text-slate-900 mb-1 flex items-center justify-between">
                    <span>Selected Pipeline</span>
                    <span className="text-[10px] font-mono bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">RandomForest</span>
                  </div>
                  <p className="text-[11px] text-slate-600 m-0">
                    ROC-AUC 97.6% | Clinical Sensitivity 93.6% at 0.40 screening threshold.
                  </p>
                </div>

                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <div className="font-bold text-slate-900 mb-1 flex items-center justify-between">
                    <span>SHAP Explainability</span>
                    <span className="text-[10px] font-mono bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">TreeExplainer</span>
                  </div>
                  <p className="text-[11px] text-slate-600 m-0">
                    Exact probability additivity showing positive and negative drivers for each individual patient.
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-4 mt-4 border-t border-slate-100">
              <Link
                href="/diabetes"
                className="text-xs font-bold text-purple-700 hover:text-purple-900 flex items-center justify-between"
              >
                <span>View Model Architecture Details</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Recent History Table Preview */}
        {history.length > 0 && (
          <section className="bg-white rounded-2xl border border-slate-200 shadow-md p-6">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900 m-0">Recent Assessment History</h3>
                <p className="text-xs text-slate-500 m-0">Your most recent clinical evaluations.</p>
              </div>
              <Link
                href="/diabetes"
                className="text-xs font-bold text-blue-700 hover:underline flex items-center gap-1"
              >
                <span>View Full Log ({history.length})</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Result</th>
                    <th className="py-2.5 px-3">Probability</th>
                    <th className="py-2.5 px-3">WHO Status</th>
                    <th className="py-2.5 px-3">Biomarkers</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {history.slice(0, 5).map((rec, i) => (
                    <tr key={rec.id || i} className="hover:bg-slate-50/60 transition">
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600">
                        {new Date(rec.timestamp).toLocaleDateString()}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase ${
                            rec.prediction?.label === 'positive'
                              ? 'bg-rose-100 text-rose-800'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {rec.prediction?.label}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-bold font-mono text-slate-800">
                        {Math.round((rec.prediction?.probability || 0) * 100)}%
                      </td>
                      <td className="py-2.5 px-3 text-slate-700 capitalize">
                        {rec.clinical_assessment?.status?.replace('_', ' ')}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600">
                        HbA1c: {rec.input?.HbA1c_level || rec.input?.hba1c_level}% | Glucose: {rec.input?.blood_glucose_level} mg/dL
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </DashboardShell>
  );
}
