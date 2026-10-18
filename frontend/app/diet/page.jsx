'use client';
import Link from 'next/link';
import { ArrowLeft, ShieldCheck, ImagePlus, ScanLine } from 'lucide-react';
import DashboardShell from '@/components/dashboard/DashboardShell';
import MealImageUpload from '@/components/diet/MealImageUpload';
import DetectionImage from '@/components/diet/DetectionImage';
import FoodDetectionResult from '@/components/diet/FoodDetectionResult';
import useDietDetection from '@/hooks/useDietDetection';
import styles from '@/components/diet/food-detection.module.css';

export default function DietPage() {
  const detection = useDietDetection();
  return <DashboardShell title="Diet · Food Detection"><div className={styles.workspace}>
    <Link className={styles.back} href="/dashboard/diet"><ArrowLeft size={15}/> Back to Diet Dashboard</Link>
    <header className={styles.header}><span className={styles.badge}><ScanLine size={13}/> AI FOOD ANALYSIS</span><h2>Sri Lankan Meal Detection</h2><p>Upload a meal image and let the AI identify supported Sri Lankan food items.</p><div className={styles.tags}><span>YOLOv8n</span><span>46 Food Classes</span><span>Food detection only</span></div></header>
    <div className={styles.grid}>
      <MealImageUpload file={detection.selectedFile} dimensions={detection.dimensions} preparing={detection.preparing} loading={detection.loading} onSelect={detection.selectFile} onAnalyze={detection.analyzeMeal} onReset={detection.resetDetection}>
        {detection.previewUrl && <DetectionImage src={detection.previewUrl} result={detection.result}/>}
      </MealImageUpload>
      <FoodDetectionResult result={detection.result} error={detection.error} loading={detection.loading} hasImage={!!detection.selectedFile} onRetry={detection.analyzeMeal} onReset={detection.resetDetection}/>
    </div>
    <aside className={styles.info}><ShieldCheck size={22}/><div><strong>A first step toward understanding your meal</strong><p>This tool identifies food items only. Portion sizes, nutrition, GI/GL and dietary recommendations are separate stages.</p></div><ImagePlus size={22} className={styles.infoEnd}/></aside>
  </div></DashboardShell>;
}
