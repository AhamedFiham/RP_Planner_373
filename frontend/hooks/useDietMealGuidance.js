'use client';
import useDietDetection from './useDietDetection';
import { analyzeMealGuidance } from '@/lib/api';
export default function useDietMealGuidance(currentGlucose, glucoseUnit) {
  return useDietDetection((file, options) => analyzeMealGuidance(file, {...options, currentGlucose, glucoseUnit}));
}
