'use client';

import { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Download,
  FileText,
  Heart,
  HelpCircle,
  Info,
  Printer,
  RefreshCw,
  Scale,
  Shield,
  ShieldAlert,
  Sparkles,
  Stethoscope,
  TrendingDown,
  TrendingUp,
  UserCheck
} from 'lucide-react';

export default function RiskResult({ data, onReset }) {
  const [viewMode, setViewMode] = useState('patient'); // 'patient' | 'clinical'

  if (!data) return null;

  const {
    prediction,
    plausibility,
    clinical_assessment,
    explainability,
    risk_factor_categories,
    personalized_awareness,
    disclaimer,
  } = data;

  const isPositive = prediction?.label === 'positive';
  const probPercent = Math.round((prediction?.probability || 0) * 100);
  const thresholdPercent = Math.round((prediction?.threshold || 0.40) * 100);
  const isHighClinical = clinical_assessment?.status === 'diabetes_range';

  const handlePrint = () => {
    if (typeof window !== 'undefined') {
      window.print();
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Controls: View Mode Switch & Export Button */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Display Mode:</span>
          <div className="flex bg-slate-100 p-1 rounded-xl">
            <button
              type="button"
              onClick={() => setViewMode('patient')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                viewMode === 'patient'
                  ? 'bg-white text-blue-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Patient-Friendly Summary
            </button>
            <button
              type="button"
              onClick={() => setViewMode('clinical')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition cursor-pointer ${
                viewMode === 'clinical'
                  ? 'bg-white text-blue-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Detailed Clinical / SHAP View
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handlePrint}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition flex items-center gap-1.5 cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Summary for Doctor</span>
          </button>
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-800 text-xs font-bold rounded-xl transition flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>New Assessment</span>
            </button>
          )}
        </div>
      </div>

      {/* SECTION 1: HERO RISK SCORE & SPEEDOMETER GAUGE */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden">
        <div className={`p-8 bg-gradient-to-br ${
          isPositive
            ? 'from-rose-950 via-slate-900 to-rose-900 text-white'
            : 'from-emerald-950 via-slate-900 to-teal-950 text-white'
        }`}>
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8">
            {/* Left: Summary Title & Context */}
            <div className="space-y-3 max-w-2xl">
              <div className="flex items-center gap-2.5">
                <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 ${
                  isPositive ? 'bg-rose-500 text-white' : 'bg-emerald-500 text-white'
                }`}>
                  {isPositive ? <AlertTriangle className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  {isPositive ? 'Increased Likelihood (Positive)' : 'Lower Predicted Likelihood'}
                </span>
                <span className="text-xs font-mono text-slate-300 bg-white/10 px-2.5 py-0.5 rounded-full border border-white/10">
                  {prediction?.model_name} AI Pipeline
                </span>
              </div>

              <h2 className="text-3xl font-extrabold tracking-tight text-white m-0">
                {isPositive ? 'Elevated Diabetes Risk Detected' : 'Lower Diabetes Probability Predicted'}
              </h2>

              <p className="text-slate-200 text-sm leading-relaxed m-0">
                {isPositive
                  ? 'The machine learning model estimated an increased statistical likelihood of diabetes based on your clinical biomarkers. This represents an educational screening estimation, not a confirmed medical diagnosis.'
                  : 'Your recorded indicators place you in a lower probability band. Continue routine preventative checkups and maintain active health habits.'}
              </p>
            </div>

            {/* Right: Circular Probability Gauge */}
            <div className="flex items-center gap-6 bg-white/10 backdrop-blur-md border border-white/15 p-6 rounded-3xl self-start lg:self-center">
              <div className="relative flex items-center justify-center">
                <svg className="w-28 h-28 transform -rotate-90">
                  <circle
                    cx="56"
                    cy="56"
                    r="46"
                    stroke="currentColor"
                    strokeWidth="10"
                    className="text-white/20"
                    fill="transparent"
                  />
                  <circle
                    cx="56"
                    cy="56"
                    r="46"
                    stroke="currentColor"
                    strokeWidth="10"
                    strokeDasharray={2 * Math.PI * 46}
                    strokeDashoffset={2 * Math.PI * 46 * (1 - probPercent / 100)}
                    strokeLinecap="round"
                    className={isPositive ? 'text-rose-400' : 'text-emerald-400'}
                    fill="transparent"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-3xl font-black text-white font-mono">{probPercent}%</span>
                  <span className="text-[10px] uppercase font-bold text-slate-300">Probability</span>
                </div>
              </div>

              <div className="space-y-1.5 text-xs">
                <div className="text-slate-300 font-semibold">Decision Cutoff:</div>
                <div className="text-white font-bold font-mono text-sm">{thresholdPercent}%</div>
                <p className="text-[11px] text-slate-300 m-0 max-w-[140px] leading-tight">
                  Calibrated for 93.6% clinical sensitivity to prevent missed cases.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Operating Domain / Reliability Warning */}
        {plausibility?.is_out_of_distribution && (
          <div className="p-4 bg-amber-50 border-t border-amber-200 text-amber-900 text-xs flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <strong className="font-bold">Model Domain Notice:</strong> {plausibility.reliability_warning}
              {plausibility.flags?.length > 0 && (
                <ul className="list-disc pl-5 mt-1 space-y-0.5">
                  {plausibility.flags.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      {/* SECTION 2: WHO CLINICAL GUIDELINE INTERPRETATION (INDEPENDENT OF ML) */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-md p-6 md:p-8">
        <div className="flex flex-wrap items-center justify-between pb-4 mb-5 border-b border-slate-100 gap-3">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-2xl ${
              isHighClinical ? 'bg-rose-100 text-rose-800' : 'bg-blue-100 text-blue-800'
            }`}>
              <Stethoscope className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 m-0">
                WHO & International Diagnostic Guideline Review
              </h3>
              <p className="text-xs text-slate-500 m-0">
                Independent evaluation based on World Health Organization (WHO 2006/2011/2019) and ADA standards.
              </p>
            </div>
          </div>

          <span className={`px-3 py-1 rounded-full text-xs font-extrabold uppercase tracking-wide border ${
            clinical_assessment?.status === 'diabetes_range'
              ? 'bg-rose-50 text-rose-700 border-rose-300'
              : clinical_assessment?.status === 'elevated_risk'
              ? 'bg-amber-50 text-amber-700 border-amber-300'
              : 'bg-emerald-50 text-emerald-700 border-emerald-300'
          }`}>
            Status: {clinical_assessment?.status?.replace('_', ' ')}
          </span>
        </div>

        <p className="text-sm text-slate-700 mb-5 font-medium">{clinical_assessment?.summary}</p>

        {/* Clinical Flags Cards */}
        {clinical_assessment?.flags?.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {clinical_assessment.flags.map((flag, idx) => {
              const isCritical = flag.severity === 'critical';
              const isWarning = flag.severity === 'warning';

              return (
                <div
                  key={idx}
                  className={`p-4 rounded-2xl border transition ${
                    isCritical
                      ? 'bg-rose-50/70 border-rose-200 text-rose-950'
                      : isWarning
                      ? 'bg-amber-50/70 border-amber-200 text-amber-950'
                      : 'bg-blue-50/70 border-blue-200 text-blue-950'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-sm flex items-center gap-1.5">
                      {isCritical && <AlertTriangle className="w-4 h-4 text-rose-600" />}
                      {flag.title}
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700">
                      {flag.category}
                    </span>
                  </div>
                  <p className="text-xs text-slate-700 m-0 leading-relaxed">{flag.description}</p>
                  <div className="mt-2.5 pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 font-mono">
                    Guideline Reference: {flag.guideline_source}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-emerald-900 text-xs flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>All recorded physiological measurements are within baseline non-diabetic ranges.</span>
          </div>
        )}

        {clinical_assessment?.requires_confirmatory_testing && (
          <div className="mt-5 p-4 bg-blue-50/80 border border-blue-200 rounded-2xl text-blue-950 text-xs flex items-start gap-3">
            <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <strong className="font-bold">Confirmatory Repeat Protocol:</strong> In asymptomatic individuals without acute metabolic crisis, international guidelines require repeating laboratory diagnostic testing on a separate day using a venous plasma sample before confirming clinical diagnosis.
            </div>
          </div>
        )}
      </div>

      {/* SECTION 3: EXPLAINABLE AI (SHAP) ATTRIBUTION */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-md p-6 md:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 mb-6 border-b border-slate-100 gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <h3 className="text-lg font-bold text-slate-900 m-0">
                Explainable AI (SHAP) — Why Did the AI Make This Prediction?
              </h3>
            </div>
            <p className="text-xs text-slate-500 m-0">
              Exact mathematical feature contributions in probability space (Base Expected Value: <span className="font-mono font-bold">{explainability?.base_value}</span>)
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs font-semibold">
            <span className="flex items-center gap-1.5 text-rose-700 bg-rose-50 px-2.5 py-1 rounded-lg border border-rose-200">
              <ArrowUpRight className="w-3.5 h-3.5 text-rose-600" /> Pushes Risk Up
            </span>
            <span className="flex items-center gap-1.5 text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
              <ArrowDownRight className="w-3.5 h-3.5 text-emerald-600" /> Pulls Risk Down
            </span>
          </div>
        </div>

        {/* Factors Breakdown Table / Visual Bars */}
        <div className="space-y-4">
          {explainability?.all_factors_ranked?.map((factor, idx) => {
            const isInc = factor.contribution_direction === 'risk_increasing';
            const isDec = factor.contribution_direction === 'risk_decreasing';
            const absShap = Math.abs(factor.shap_value);
            const barWidthPercent = Math.min(100, Math.max(6, Math.round(absShap * 250)));

            return (
              <div
                key={idx}
                className="p-4 rounded-2xl border border-slate-100 bg-slate-50/50 hover:bg-white hover:border-slate-300 hover:shadow-sm transition"
              >
                <div className="flex flex-wrap items-center justify-between text-xs mb-2 gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] font-bold text-slate-400 w-5">
                      #{factor.contribution_rank}
                    </span>
                    <span className="font-bold text-slate-800 text-sm">{factor.feature_label}</span>
                    <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 font-mono text-[11px] text-slate-700 font-bold">
                      {factor.patient_value}
                    </span>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                      {factor.risk_category?.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 font-mono font-bold text-sm">
                    <span className={isInc ? 'text-rose-600' : isDec ? 'text-emerald-600' : 'text-slate-500'}>
                      {factor.shap_value > 0 ? `+${(factor.shap_value * 100).toFixed(2)}%` : `${(factor.shap_value * 100).toFixed(2)}%`}
                    </span>
                  </div>
                </div>

                {/* Progress Bar Container */}
                <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden my-2 flex">
                  {isDec ? (
                    <div
                      className="bg-gradient-to-l from-emerald-500 to-teal-400 h-full rounded-full ml-auto transition-all duration-500"
                      style={{ width: `${barWidthPercent}%` }}
                    ></div>
                  ) : (
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isInc ? 'bg-gradient-to-r from-rose-500 to-amber-500' : 'bg-slate-400'
                      }`}
                      style={{ width: `${barWidthPercent}%` }}
                    ></div>
                  )}
                </div>

                <p className="text-xs text-slate-600 m-0 mt-1.5 font-medium leading-relaxed">
                  {factor.explanation}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* SECTION 4: RISK FACTOR CATEGORIES (MODIFIABLE / NON-MODIFIABLE / CLINICAL) */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-md p-6 md:p-8">
        <div className="pb-4 mb-6 border-b border-slate-100">
          <h3 className="text-lg font-bold text-slate-900 m-0">
            Categorized Clinical Risk Profiling
          </h3>
          <p className="text-xs text-slate-500 m-0">
            Separates factors into modifiable actions you can influence, non-modifiable demographic factors, and conditions needing clinical care.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Card A: Modifiable */}
          <div className="border border-emerald-200 bg-emerald-50/30 rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-xl bg-emerald-100 text-emerald-800">
                    <Scale className="w-4 h-4" />
                  </span>
                  <h4 className="font-bold text-sm text-emerald-950 m-0">
                    Modifiable Factors
                  </h4>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded-full">
                  Actionable
                </span>
              </div>
              <p className="text-xs text-slate-600 mb-4 leading-relaxed">
                {risk_factor_categories?.modifiable?.description}
              </p>
              <div className="space-y-3">
                {risk_factor_categories?.modifiable?.factors?.map((f, idx) => (
                  <div key={idx} className="bg-white p-3 rounded-xl border border-emerald-100 shadow-xs text-xs">
                    <div className="flex items-center justify-between font-bold text-slate-800 mb-1">
                      <span>{f.name}</span>
                      <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-mono">
                        {f.value}
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px] m-0">{f.clinical_note}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Card B: Non-Modifiable */}
          <div className="border border-blue-200 bg-blue-50/30 rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-xl bg-blue-100 text-blue-800">
                    <UserCheck className="w-4 h-4" />
                  </span>
                  <h4 className="font-bold text-sm text-blue-950 m-0">
                    Non-Modifiable Factors
                  </h4>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-200 text-blue-900 px-2 py-0.5 rounded-full">
                  Inherent
                </span>
              </div>
              <p className="text-xs text-slate-600 mb-4 leading-relaxed">
                {risk_factor_categories?.non_modifiable?.description}
              </p>
              <div className="space-y-3">
                {risk_factor_categories?.non_modifiable?.factors?.map((f, idx) => (
                  <div key={idx} className="bg-white p-3 rounded-xl border border-blue-100 shadow-xs text-xs">
                    <div className="flex items-center justify-between font-bold text-slate-800 mb-1">
                      <span>{f.name}</span>
                      <span className="text-blue-700 bg-blue-50 px-2 py-0.5 rounded font-mono">
                        {f.value}
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px] m-0">{f.clinical_note}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Card C: Manageable Clinical */}
          <div className="border border-purple-200 bg-purple-50/30 rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-xl bg-purple-100 text-purple-800">
                    <Activity className="w-4 h-4" />
                  </span>
                  <h4 className="font-bold text-sm text-purple-950 m-0">
                    Manageable Clinical
                  </h4>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-purple-200 text-purple-900 px-2 py-0.5 rounded-full">
                  Clinical Care
                </span>
              </div>
              <p className="text-xs text-slate-600 mb-4 leading-relaxed">
                {risk_factor_categories?.manageable_clinical?.description}
              </p>
              <div className="space-y-3">
                {risk_factor_categories?.manageable_clinical?.factors?.map((f, idx) => (
                  <div key={idx} className="bg-white p-3 rounded-xl border border-purple-100 shadow-xs text-xs">
                    <div className="flex items-center justify-between font-bold text-slate-800 mb-1">
                      <span>{f.name}</span>
                      <span className="text-purple-700 bg-purple-50 px-2 py-0.5 rounded font-mono">
                        {f.value}
                      </span>
                    </div>
                    <p className="text-slate-600 text-[11px] m-0">{f.clinical_note}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 5: PERSONALIZED DIABETES AWARENESS & ACTION PLAN */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-md p-6 md:p-8">
        <div className="pb-4 mb-6 border-b border-slate-100">
          <div className="flex items-center gap-2 mb-1">
            <Heart className="w-5 h-5 text-rose-600" />
            <h3 className="text-lg font-bold text-slate-900 m-0">
              Personalized Diabetes Action & Care Plan
            </h3>
          </div>
          <p className="text-xs text-slate-500 m-0">
            Synthesized from patient-specific measurements, SHAP drivers, and WHO clinical protocols.
          </p>
        </div>

        {/* Prediction Narrative Summary */}
        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 text-xs text-slate-800 leading-relaxed mb-6 font-medium">
          <strong className="text-slate-900">Clinical Interpretation Summary:</strong>{' '}
          {personalized_awareness?.prediction_explanation}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Card 1: Lifestyle */}
          <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/50">
            <h4 className="font-bold text-sm text-slate-900 mb-3 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              Modifiable Lifestyle Recommendations
            </h4>
            <ul className="text-xs text-slate-700 space-y-2.5 pl-4 list-disc m-0">
              {personalized_awareness?.lifestyle_awareness?.map((item, idx) => (
                <li key={idx} className="leading-relaxed">{item}</li>
              ))}
            </ul>
          </div>

          {/* Card 2: Medical Oversight */}
          <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/50">
            <h4 className="font-bold text-sm text-slate-900 mb-3 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
              Medical & Glycemic Management
            </h4>
            <ul className="text-xs text-slate-700 space-y-2.5 pl-4 list-disc m-0">
              {personalized_awareness?.medical_awareness?.map((item, idx) => (
                <li key={idx} className="leading-relaxed">{item}</li>
              ))}
            </ul>
          </div>

          {/* Card 3: Screening Guidance */}
          <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/50">
            <h4 className="font-bold text-sm text-slate-900 mb-3 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
              Recommended Complication Screenings
            </h4>
            <ul className="text-xs text-slate-700 space-y-2.5 pl-4 list-disc m-0">
              {personalized_awareness?.screening_guidance?.map((item, idx) => (
                <li key={idx} className="leading-relaxed">{item}</li>
              ))}
            </ul>
          </div>

          {/* Card 4: Next Steps */}
          <div className="p-5 rounded-2xl border border-indigo-200 bg-indigo-50/40">
            <h4 className="font-bold text-sm text-indigo-950 mb-3 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-600"></span>
              Immediate Clinical Next Steps
            </h4>
            <ul className="text-xs text-indigo-950 space-y-2.5 pl-4 list-disc m-0 font-medium">
              {personalized_awareness?.recommended_next_steps?.map((item, idx) => (
                <li key={idx} className="leading-relaxed">{item}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Disclaimer Notice */}
        <div className="mt-8 pt-4 border-t border-slate-100 text-[11px] text-slate-500 italic text-center">
          {disclaimer}
        </div>
      </div>
    </div>
  );
}
