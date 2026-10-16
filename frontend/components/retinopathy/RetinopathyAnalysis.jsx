'use client';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/components/auth-provider';
import { createRetinopathyApi } from '@/lib/retinopathy/api';
import useRetinopathyAnalysis from '@/hooks/useRetinopathyAnalysis';
import DashboardShell from '@/components/dashboard/DashboardShell';
import RetinalImageUpload from './RetinalImageUpload';
import ImageQualityAssessment from './ImageQualityAssessment';
import RetinopathyResult from './RetinopathyResult';
import RetinopathyHistory from './RetinopathyHistory';
import RetinopathyDisclaimer from './RetinopathyDisclaimer';

export default function RetinopathyAnalysis() {
  const { token, user, logout } = useAuth();
  const logoutRef = useRef(logout); logoutRef.current = logout;
  const api = useMemo(() => createRetinopathyApi(token, () => logoutRef.current()), [token]);
  // Synchronously discard all patient state on logout/account switch, not just after an effect.
  return token ? <PatientAnalysis key={`${token}:${user?.email || ''}`} api={api} /> : null;
}
function PatientAnalysis({ api }) {
  const analysis = useRetinopathyAnalysis(api);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState('');
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    api.health(controller.signal).then(value => { if (active) setHealth(value); }).catch(error => { if (active) setHealthError(error.message); });
    return () => { active = false; controller.abort(); };
  }, [api]);
  const { status, selectedImage, error, quality, result, selectImage, reset, analyze, historyRevision } = analysis;
  return <DashboardShell title="Retinopathy Analysis"><div className="retino-page" data-state={status}>
    <header className="retino-page-header"><div><div className="retino-breadcrumb"><Link href="/dashboard">Dashboard</Link><ArrowRight size={13} /><strong>Retinopathy Analysis</strong></div><div className="retino-title-line"><div><p className="retino-kicker">AI-ASSISTED RETINAL SCREENING</p><h2>Diabetic Retinopathy Analysis</h2><p>Upload a retinal fundus image to assess diabetic retinopathy severity and explore AI-generated visual explanations.</p></div><span className="retino-header-badge"><CheckCircle2 size={15} /> AI-Assisted Retinal Screening</span></div></div></header>
    <div className="retino-demo-banner" role="status"><span>Research analysis service</span><p>{healthError || (health ? health.ready ? 'Required analysis models are ready. Results require professional review.' : 'The retinal analysis service is unavailable: required models are not ready. No quality gate will be bypassed.' : 'Checking model availability…')}</p></div>
    <div className="retino-top-grid"><RetinalImageUpload selectedImage={selectedImage} onSelect={selectImage} onRemove={reset} onAnalyze={analyze} error={error} status={status} /><div className="retino-quality-slot"><ImageQualityAssessment quality={quality} onUploadAnother={reset} />{!quality && <div className="retino-empty-quality"><span>2</span><div><strong>Quality gate</strong><p>Actual image quality feedback will appear after analysis.</p></div></div>}</div></div>
    {status === 'quality_rejected' && <div className="retino-rejected-callout"><strong>Severity analysis stopped.</strong><span>Upload a clearer retinal image to continue.</span><button type="button" className="retino-button ghost" onClick={reset}>Upload another image</button></div>}
    {result && <RetinopathyResult result={result} api={api} />}
    <div className="retino-history-section"><RetinopathyHistory api={api} revision={historyRevision} onDeleted={analysis.clearDeleted} /></div>
    <RetinopathyDisclaimer />
  </div></DashboardShell>;
}
