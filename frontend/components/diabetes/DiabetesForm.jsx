'use client';

import { useState } from 'react';
import {
  Activity,
  Heart,
  User,
  ShieldAlert,
  Flame,
  Scale,
  Sparkles,
  Info,
  CheckCircle2,
  AlertCircle,
  FileCheck2,
  Stethoscope,
  HelpCircle,
  Check
} from 'lucide-react';

const PRESET_PROFILES = {
  normal: {
    id: 'normal',
    title: 'Healthy Baseline Profile',
    desc: 'Normal HbA1c (5.2%) & fasting glucose (95 mg/dL)',
    tag: 'Normal / Non-Diabetic',
    tagColor: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    data: {
      gender: 'Female',
      age: 32,
      hypertension: 0,
      heart_disease: 0,
      smoking_history: 'never',
      bmi: 22.4,
      HbA1c_level: 5.2,
      blood_glucose_level: 95,
      glucose_context: 'fasting',
      hba1c_lab_confirmed: true,
    }
  },
  prediabetes: {
    id: 'prediabetes',
    title: 'Pre-Diabetes Profile',
    desc: 'Elevated HbA1c (6.0%) & overweight BMI (27.8)',
    tag: 'Intermediate Risk',
    tagColor: 'bg-amber-100 text-amber-800 border-amber-300',
    data: {
      gender: 'Female',
      age: 49,
      hypertension: 0,
      heart_disease: 0,
      smoking_history: 'never',
      bmi: 27.8,
      HbA1c_level: 6.0,
      blood_glucose_level: 118,
      glucose_context: 'fasting',
      hba1c_lab_confirmed: true,
    }
  },
  high_risk: {
    id: 'high_risk',
    title: 'High Risk Profile',
    desc: 'HbA1c ≥ 6.5% (7.2%), fasting glucose 185 mg/dL, hypertension',
    tag: 'Elevated Likelihood',
    tagColor: 'bg-rose-100 text-rose-800 border-rose-300',
    data: {
      gender: 'Male',
      age: 58,
      hypertension: 1,
      heart_disease: 1,
      smoking_history: 'former',
      bmi: 33.5,
      HbA1c_level: 7.2,
      blood_glucose_level: 185,
      glucose_context: 'fasting',
      hba1c_lab_confirmed: true,
    }
  },
};

export default function DiabetesForm({ onSubmit, loading, error }) {
  const [formData, setFormData] = useState(PRESET_PROFILES.prediabetes.data);
  const [activePreset, setActivePreset] = useState('prediabetes');
  const [formErrors, setFormErrors] = useState({});

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    setActivePreset(null);
    if (formErrors[name]) {
      setFormErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const loadPreset = (key) => {
    setFormData(PRESET_PROFILES[key].data);
    setActivePreset(key);
    setFormErrors({});
  };

  // Real-time clinical interpretation indicators for intuitive understanding
  const getBmiStatus = (bmi) => {
    const val = Number(bmi);
    if (!val || isNaN(val)) return null;
    if (val < 18.5) return { label: 'Underweight (<18.5)', color: 'text-blue-600 bg-blue-50 border-blue-200' };
    if (val < 25.0) return { label: 'Healthy Weight (18.5–24.9)', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
    if (val < 30.0) return { label: 'Overweight (25.0–29.9)', color: 'text-amber-700 bg-amber-50 border-amber-200' };
    return { label: 'Obese (≥30.0)', color: 'text-rose-700 bg-rose-50 border-rose-200' };
  };

  const getHba1cStatus = (hba1c) => {
    const val = Number(hba1c);
    if (!val || isNaN(val)) return null;
    if (val < 5.7) return { label: 'Normal (<5.7%)', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
    if (val < 6.5) return { label: 'Pre-Diabetes Range (5.7%–6.4%)', color: 'text-amber-700 bg-amber-50 border-amber-200' };
    return { label: 'Diabetes Diagnostic Range (≥6.5%)', color: 'text-rose-700 bg-rose-50 border-rose-200' };
  };

  const getGlucoseStatus = (bg, context) => {
    const val = Number(bg);
    if (!val || isNaN(val)) return null;
    if (context === 'fasting') {
      if (val < 100) return { label: 'Normal Fasting (<100 mg/dL)', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
      if (val < 126) return { label: 'Impaired Fasting Glucose (100–125)', color: 'text-amber-700 bg-amber-50 border-amber-200' };
      return { label: 'Fasting Diabetes Threshold (≥126)', color: 'text-rose-700 bg-rose-50 border-rose-200' };
    }
    if (val >= 200) return { label: 'Markedly Elevated (≥200 mg/dL)', color: 'text-rose-700 bg-rose-50 border-rose-200' };
    if (val >= 140) return { label: 'Elevated Post-Meal (≥140)', color: 'text-amber-700 bg-amber-50 border-amber-200' };
    return { label: 'Normal Range', color: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
  };

  const bmiIndicator = getBmiStatus(formData.bmi);
  const hba1cIndicator = getHba1cStatus(formData.HbA1c_level);
  const glucoseIndicator = getGlucoseStatus(formData.blood_glucose_level, formData.glucose_context);

  const validate = () => {
    const errors = {};
    if (formData.age === '' || isNaN(formData.age) || Number(formData.age) < 0 || Number(formData.age) > 120) {
      errors.age = 'Age must be between 0 and 120 years.';
    }
    if (formData.bmi === '' || isNaN(formData.bmi) || Number(formData.bmi) < 10 || Number(formData.bmi) > 100) {
      errors.bmi = 'BMI must be between 10.0 and 100.0 kg/m².';
    }
    if (formData.HbA1c_level === '' || isNaN(formData.HbA1c_level) || Number(formData.HbA1c_level) < 3.0 || Number(formData.HbA1c_level) > 20.0) {
      errors.HbA1c_level = 'HbA1c must be between 3.0% and 20.0%.';
    }
    if (formData.blood_glucose_level === '' || isNaN(formData.blood_glucose_level) || Number(formData.blood_glucose_level) < 30 || Number(formData.blood_glucose_level) > 750) {
      errors.blood_glucose_level = 'Blood glucose must be between 30 and 750 mg/dL.';
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;

    const payload = {
      gender: formData.gender,
      age: Number(formData.age),
      hypertension: Number(formData.hypertension),
      heart_disease: Number(formData.heart_disease),
      smoking_history: formData.smoking_history,
      bmi: Number(formData.bmi),
      HbA1c_level: Number(formData.HbA1c_level),
      blood_glucose_level: Number(formData.blood_glucose_level),
      glucose_context: formData.glucose_context,
      hba1c_lab_confirmed: Boolean(formData.hba1c_lab_confirmed),
    };

    onSubmit(payload);
  };

  return (
    <div className="space-y-6">
      {/* 3-Step Interactive Process Explanation Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm flex items-start gap-3">
          <div className="w-8 h-8 rounded-xl bg-blue-100 text-blue-700 font-bold flex items-center justify-center shrink-0 text-sm">
            1
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider m-0">Input Biomarkers</h4>
            <p className="text-xs text-slate-500 m-0 mt-0.5 leading-relaxed">
              Enter routine glucose, HbA1c, and lifestyle indicators or choose a preset test profile below.
            </p>
          </div>
        </div>

        <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm flex items-start gap-3">
          <div className="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center shrink-0 text-sm">
            2
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider m-0">Dual-Engine Analysis</h4>
            <p className="text-xs text-slate-500 m-0 mt-0.5 leading-relaxed">
              Independent WHO clinical guidelines and a 97.6% ROC-AUC machine learning model evaluate the data.
            </p>
          </div>
        </div>

        <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-sm flex items-start gap-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center shrink-0 text-sm">
            3
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider m-0">Explainable AI (SHAP)</h4>
            <p className="text-xs text-slate-500 m-0 mt-0.5 leading-relaxed">
              See the exact mathematical factors that increased or reduced your risk with clinical next steps.
            </p>
          </div>
        </div>
      </div>

      {/* Preset Profiles Selector Cards */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between pb-3 mb-4 border-b border-slate-100 gap-2">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider m-0 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <span>Select a Test Patient Profile or Enter Custom Measurements</span>
            </h3>
            <p className="text-xs text-slate-500 m-0 mt-0.5">
              Click any profile below to instantly load real clinical test cases and see how the system responds.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(PRESET_PROFILES).map(([key, item]) => {
            const isSelected = activePreset === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => loadPreset(key)}
                className={`p-4 rounded-xl border text-left transition relative cursor-pointer ${
                  isSelected
                    ? 'bg-blue-50/70 border-blue-500 shadow-sm ring-2 ring-blue-500/20'
                    : 'bg-slate-50/50 hover:bg-white border-slate-200 hover:border-slate-300'
                }`}
              >
                {isSelected && (
                  <span className="absolute top-3 right-3 w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs">
                    <Check className="w-3 h-3 stroke-[3]" />
                  </span>
                )}
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${item.tagColor}`}>
                    {item.tag}
                  </span>
                </div>
                <h4 className="font-bold text-sm text-slate-900 m-0 mb-1">{item.title}</h4>
                <p className="text-xs text-slate-500 m-0 leading-relaxed">{item.desc}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Clinical Assessment Input Form */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
        {/* Form Title Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 p-6 text-white">
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 bg-blue-500/20 text-blue-300 rounded-lg border border-blue-400/30">
              <Stethoscope className="w-4 h-4" />
            </span>
            <span className="text-xs font-semibold tracking-wider uppercase text-blue-300 font-mono">
              Patient Assessment Form
            </span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white m-0">
            Biomarkers & Health History
          </h2>
          <p className="text-slate-300 text-xs mt-1 m-0">
            All fields marked with <span className="text-rose-400">*</span> are mandatory for machine learning inference.
          </p>
        </div>

        {error && (
          <div className="m-6 p-4 bg-rose-50 border border-rose-200 text-rose-800 text-sm rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Evaluation Error:</strong> {error}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="p-6 md:p-8 space-y-8">
          {/* SECTION A: DEMOGRAPHICS & BEHAVIORAL FACTORS */}
          <div>
            <div className="flex items-center gap-2 pb-2 mb-4 border-b border-slate-100">
              <User className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 m-0">
                1. Demographics & Lifestyle
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Gender */}
              <div>
                <label className="custom-label block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5" htmlFor="gender">
                  Gender <span className="text-rose-500">*</span>
                </label>
                <select
                  id="gender"
                  name="gender"
                  value={formData.gender}
                  onChange={handleChange}
                  className="w-full bg-slate-50/70 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 transition"
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                </select>
                <span className="text-[11px] text-slate-400 mt-1 block">Demographic risk variable</span>
              </div>

              {/* Age */}
              <div>
                <label className="custom-label block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5" htmlFor="age">
                  Age (Years) <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type="number"
                    id="age"
                    name="age"
                    min="0"
                    max="120"
                    value={formData.age}
                    onChange={handleChange}
                    placeholder="e.g. 45"
                    className={`custom-input w-full bg-slate-50/70 border rounded-xl pl-3.5 pr-12 py-2.5 text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 transition ${
                      formErrors.age ? 'border-rose-400 bg-rose-50/40' : 'border-slate-200'
                    }`}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-semibold text-slate-400 pointer-events-none">
                    yrs
                  </span>
                </div>
                {formErrors.age ? (
                  <span className="text-[11px] text-rose-600 mt-1 block">{formErrors.age}</span>
                ) : (
                  <span className="text-[11px] text-slate-400 mt-1 block">Age in completed years (0–120)</span>
                )}
              </div>

              {/* Smoking History */}
              <div>
                <label className="custom-label block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5" htmlFor="smoking_history">
                  Smoking Status <span className="text-rose-500">*</span>
                </label>
                <select
                  id="smoking_history"
                  name="smoking_history"
                  value={formData.smoking_history}
                  onChange={handleChange}
                  className="w-full bg-slate-50/70 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 transition"
                >
                  <option value="never">Never smoked (Protective)</option>
                  <option value="current">Current smoker (Modifiable Risk)</option>
                  <option value="former">Former smoker (Historical Exposure)</option>
                  <option value="not current">Not current smoker</option>
                  <option value="ever">Ever smoked</option>
                  <option value="No Info">No Information provided</option>
                </select>
                <span className="text-[11px] text-slate-400 mt-1 block">Trained categorical feature</span>
              </div>
            </div>
          </div>

          {/* SECTION B: CLINICAL BIOMARKERS WITH LIVE STATUS INDICATOR */}
          <div>
            <div className="flex items-center gap-2 pb-2 mb-4 border-b border-slate-100">
              <Activity className="w-4 h-4 text-emerald-600" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 m-0">
                2. Clinical Biomarkers & Live Diagnostic Ranges
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* BMI with live indicator */}
              <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-200">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="custom-label block text-xs font-bold uppercase tracking-wider text-slate-700 m-0" htmlFor="bmi">
                    Body Mass Index (BMI) <span className="text-rose-500">*</span>
                  </label>
                  <Scale className="w-4 h-4 text-slate-400" />
                </div>
                <div className="relative">
                  <input
                    type="number"
                    id="bmi"
                    name="bmi"
                    step="0.1"
                    value={formData.bmi}
                    onChange={handleChange}
                    placeholder="e.g. 26.5"
                    className={`custom-input w-full bg-white border rounded-xl pl-3.5 pr-14 py-2.5 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 transition ${
                      formErrors.bmi ? 'border-rose-400 bg-rose-50/40' : 'border-slate-300'
                    }`}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 pointer-events-none">
                    kg/m²
                  </span>
                </div>
                {/* Live Real-Time Clinical Indicator */}
                {bmiIndicator && (
                  <div className={`mt-2.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border flex items-center justify-between ${bmiIndicator.color}`}>
                    <span>WHO Classification:</span>
                    <span>{bmiIndicator.label}</span>
                  </div>
                )}
              </div>

              {/* HbA1c with live indicator */}
              <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-200">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="custom-label block text-xs font-bold uppercase tracking-wider text-slate-700 m-0" htmlFor="HbA1c_level">
                    HbA1c Glycated Hemoglobin <span className="text-rose-500">*</span>
                  </label>
                  <Flame className="w-4 h-4 text-amber-500" />
                </div>
                <div className="relative">
                  <input
                    type="number"
                    id="HbA1c_level"
                    name="HbA1c_level"
                    step="0.1"
                    value={formData.HbA1c_level}
                    onChange={handleChange}
                    placeholder="e.g. 5.8"
                    className={`custom-input w-full bg-white border rounded-xl pl-3.5 pr-10 py-2.5 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 transition ${
                      formErrors.HbA1c_level ? 'border-rose-400 bg-rose-50/40' : 'border-slate-300'
                    }`}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 pointer-events-none">
                    %
                  </span>
                </div>
                {/* Live Real-Time Clinical Indicator */}
                {hba1cIndicator && (
                  <div className={`mt-2.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border flex items-center justify-between ${hba1cIndicator.color}`}>
                    <span>Clinical Status:</span>
                    <span>{hba1cIndicator.label}</span>
                  </div>
                )}
              </div>

              {/* Blood Glucose with live indicator */}
              <div className="bg-slate-50/50 p-4 rounded-2xl border border-slate-200">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="custom-label block text-xs font-bold uppercase tracking-wider text-slate-700 m-0" htmlFor="blood_glucose_level">
                    Blood Glucose Concentration <span className="text-rose-500">*</span>
                  </label>
                  <Activity className="w-4 h-4 text-blue-500" />
                </div>
                <div className="relative">
                  <input
                    type="number"
                    id="blood_glucose_level"
                    name="blood_glucose_level"
                    step="1"
                    value={formData.blood_glucose_level}
                    onChange={handleChange}
                    placeholder="e.g. 110"
                    className={`custom-input w-full bg-white border rounded-xl pl-3.5 pr-14 py-2.5 text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 transition ${
                      formErrors.blood_glucose_level ? 'border-rose-400 bg-rose-50/40' : 'border-slate-300'
                    }`}
                  />
                  <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-400 pointer-events-none">
                    mg/dL
                  </span>
                </div>
                {/* Live Real-Time Clinical Indicator */}
                {glucoseIndicator && (
                  <div className={`mt-2.5 px-2.5 py-1 rounded-lg text-[11px] font-bold border flex items-center justify-between ${glucoseIndicator.color}`}>
                    <span>Glycemic Status:</span>
                    <span>{glucoseIndicator.label}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* SECTION C: CLINICAL CONTEXT & CARDIOVASCULAR CONDITIONS */}
          <div>
            <div className="flex items-center gap-2 pb-2 mb-4 border-b border-slate-100">
              <Heart className="w-4 h-4 text-rose-600" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700 m-0">
                3. Clinical Context & Cardiovascular Comorbidities
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Glucose Context */}
              <div className="bg-blue-50/40 p-4 rounded-2xl border border-blue-100 flex flex-col justify-between">
                <div>
                  <label className="custom-label block text-xs font-bold uppercase tracking-wider text-blue-950 mb-1.5" htmlFor="glucose_context">
                    Glucose Timing / Context
                  </label>
                  <select
                    id="glucose_context"
                    name="glucose_context"
                    value={formData.glucose_context}
                    onChange={handleChange}
                    className="w-full bg-white border border-blue-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-600/30 focus:border-blue-600 transition"
                  >
                    <option value="fasting">Fasting (&gt;8 hours without calories)</option>
                    <option value="random">Random (independent of meals)</option>
                    <option value="two_hour_ogtt">2-Hour Post 75g Glucose (OGTT)</option>
                    <option value="unknown">Context Unspecified / Unknown</option>
                  </select>
                </div>
                <span className="text-[11px] text-blue-700 mt-2 block">
                  Ensures correct WHO diagnostic threshold application.
                </span>
              </div>

              {/* Hypertension Card Toggle */}
              <div
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    hypertension: prev.hypertension === 1 ? 0 : 1,
                  }))
                }
                className={`p-4 rounded-2xl border cursor-pointer select-none transition flex items-center justify-between ${
                  formData.hypertension === 1
                    ? 'bg-rose-50/80 border-rose-300 text-rose-950 shadow-sm ring-1 ring-rose-300'
                    : 'bg-slate-50/60 hover:bg-slate-50 border-slate-200 text-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${formData.hypertension === 1 ? 'bg-rose-200 text-rose-800' : 'bg-slate-200 text-slate-600'}`}>
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wide">Hypertension History</div>
                    <div className="text-[11px] text-slate-500">Diagnosed high blood pressure</div>
                  </div>
                </div>
                <span className={`text-xs font-extrabold px-3 py-1 rounded-full uppercase ${
                  formData.hypertension === 1 ? 'bg-rose-600 text-white shadow-xs' : 'bg-slate-200 text-slate-700'
                }`}>
                  {formData.hypertension === 1 ? 'Yes' : 'No'}
                </span>
              </div>

              {/* Heart Disease Card Toggle */}
              <div
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    heart_disease: prev.heart_disease === 1 ? 0 : 1,
                  }))
                }
                className={`p-4 rounded-2xl border cursor-pointer select-none transition flex items-center justify-between ${
                  formData.heart_disease === 1
                    ? 'bg-rose-50/80 border-rose-300 text-rose-950 shadow-sm ring-1 ring-rose-300'
                    : 'bg-slate-50/60 hover:bg-slate-50 border-slate-200 text-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${formData.heart_disease === 1 ? 'bg-rose-200 text-rose-800' : 'bg-slate-200 text-slate-600'}`}>
                    <Heart className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wide">Heart Disease History</div>
                    <div className="text-[11px] text-slate-500">Established cardiovascular disease</div>
                  </div>
                </div>
                <span className={`text-xs font-extrabold px-3 py-1 rounded-full uppercase ${
                  formData.heart_disease === 1 ? 'bg-rose-600 text-white shadow-xs' : 'bg-slate-200 text-slate-700'
                }`}>
                  {formData.heart_disease === 1 ? 'Yes' : 'No'}
                </span>
              </div>
            </div>

            {/* Quality Notice Checkbox */}
            <div className="mt-5 flex items-center gap-2.5 text-xs text-slate-600 bg-slate-50 p-4 rounded-xl border border-slate-200">
              <FileCheck2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <label className="custom-label flex items-center gap-2.5 cursor-pointer font-medium m-0">
                <input
                  type="checkbox"
                  name="hba1c_lab_confirmed"
                  checked={formData.hba1c_lab_confirmed}
                  onChange={handleChange}
                  className="w-4 h-4 text-blue-600 rounded border-slate-300"
                />
                <span>HbA1c value was measured using a certified clinical laboratory assay (NGSP/IFCC standardized)</span>
              </label>
            </div>
          </div>

          {/* Action Button */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-end">
            <button
              type="submit"
              disabled={loading}
              className="w-full md:w-auto px-10 py-4 bg-gradient-to-r from-blue-700 via-indigo-700 to-blue-800 hover:from-blue-800 hover:to-indigo-900 text-white font-extrabold text-sm rounded-xl shadow-lg shadow-blue-900/30 hover:shadow-xl transition transform active:scale-[0.99] flex items-center justify-center gap-2.5 disabled:opacity-60 cursor-pointer"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Computing Clinical SHAP Factors...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Run Explainable Risk Assessment</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
