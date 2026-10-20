'use client';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import DashboardShell from '@/components/dashboard/DashboardShell';
import MealImageUpload from '@/components/diet/MealImageUpload';
import DetectionImage from '@/components/diet/DetectionImage';
import FoodDetectionResult from '@/components/diet/FoodDetectionResult';
import useDietMealGuidance from '@/hooks/useDietMealGuidance';
import { useState } from 'react';
import { validateGlucoseInput } from '@/lib/diet-detection';
import styles from '@/components/diet/food-detection.module.css';

export default function DietPage() {
  const [glucose, setGlucose] = useState('');
  const [unit, setUnit] = useState('mg/dL');
  const [glucoseError, setGlucoseError] = useState(null);
  const detection = useDietMealGuidance(glucose, unit);

  function handleAnalyze() {
    const errorMsg = validateGlucoseInput(glucose, unit);
    if (errorMsg) {
      setGlucoseError(errorMsg);
      return;
    }
    setGlucoseError(null);
    detection.analyzeMeal();
  }

  function handleReset() {
    setGlucoseError(null);
    detection.resetDetection();
  }

  return (
    <DashboardShell title="Nutrition & Diet">
      <div className={styles.workspace}>
        <Link className={styles.back} href="/dashboard/diet">
          <ArrowLeft size={15} /> Back to Diet Dashboard
        </Link>
        <header className={styles.header}>
          <h2>Understand your meal</h2>
          <p>Explore the foods on your plate, their portions, and reference nutrition—all from one photo.</p>
        </header>
        <div className={styles.glucoseInput}>
          <label htmlFor="current-glucose">Current Glucose Level</label>
          <div>
            <input
              id="current-glucose"
              inputMode="decimal"
              value={glucose}
              onChange={e => {
                setGlucose(e.target.value);
                if (glucoseError) setGlucoseError(null);
              }}
              placeholder="Enter level"
            />
            <select
              value={unit}
              onChange={e => {
                setUnit(e.target.value);
                if (glucoseError) setGlucoseError(null);
              }}
              aria-label="Glucose unit"
            >
              <option value="mg/dL">mg/dL</option>
              <option value="mmol/L">mmol/L</option>
            </select>
          </div>
          {glucoseError ? (
            <p className={styles.glucoseInlineError} role="alert">{glucoseError}</p>
          ) : (
            <small>Enter your current glucose level to receive meal guidance.</small>
          )}
        </div>
        <div className={styles.grid}>
          <MealImageUpload
            file={detection.selectedFile}
            dimensions={detection.dimensions}
            preparing={detection.preparing}
            loading={detection.loading}
            onSelect={detection.selectFile}
            onAnalyze={handleAnalyze}
            onReset={handleReset}
          >
            {detection.previewUrl && <DetectionImage src={detection.previewUrl} result={detection.result} />}
          </MealImageUpload>
          <FoodDetectionResult
            result={detection.result}
            error={detection.error}
            loading={detection.loading}
            hasImage={!!detection.selectedFile}
            onRetry={handleAnalyze}
            onReset={handleReset}
          />
        </div>
        <p className={styles.patientDisclaimer}>
          Meal guidance is educational and based on reference nutrition and the glucose value entered. Follow your healthcare professional’s diabetes plan.
        </p>
      </div>
    </DashboardShell>
  );
}
