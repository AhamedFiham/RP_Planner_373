'use client';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import DashboardShell from '@/components/dashboard/DashboardShell';
import MealImageUpload from '@/components/diet/MealImageUpload';
import DetectionImage from '@/components/diet/DetectionImage';
import FoodDetectionResult from '@/components/diet/FoodDetectionResult';
import useDietConsumedNutrition from '@/hooks/useDietConsumedNutrition';
import styles from '@/components/diet/food-detection.module.css';

export default function DietPage() {
  const detection = useDietConsumedNutrition();
  return <DashboardShell title="Nutrition & Diet"><div className={styles.workspace}>
    <Link className={styles.back} href="/dashboard/diet"><ArrowLeft size={15}/> Back to Diet Dashboard</Link>
    <header className={styles.header}><h2>Understand your meal</h2><p>Explore the foods on your plate, their portions, and reference nutrition—all from one photo.</p></header>
    <div className={styles.grid}>
      <MealImageUpload file={detection.selectedFile} dimensions={detection.dimensions} preparing={detection.preparing} loading={detection.loading} onSelect={detection.selectFile} onAnalyze={detection.analyzeMeal} onReset={detection.resetDetection}>
        {detection.previewUrl && <DetectionImage src={detection.previewUrl} result={detection.result}/>}
      </MealImageUpload>
      <FoodDetectionResult result={detection.result} error={detection.error} loading={detection.loading} hasImage={!!detection.selectedFile} onRetry={detection.analyzeMeal} onReset={detection.resetDetection}/>
    </div>
    <p className={styles.patientDisclaimer}>Nutrition values are reference estimates and may vary depending on ingredients and preparation.</p>
  </div></DashboardShell>;
}
