'use client';
import useDietDetection from './useDietDetection';
import { estimateMealConsumedNutrition } from '@/lib/api';
export default function useDietConsumedNutrition() {
  const state=useDietDetection(estimateMealConsumedNutrition);
  return {...state, reset:state.resetDetection};
}
