'use client';
import useDietDetection from './useDietDetection';
import { mapMealNutrition } from '@/lib/api';

export default function useDietNutritionMapping() {
  const state = useDietDetection(mapMealNutrition);
  return { ...state, analyzeMeal: state.analyzeMeal, reset: state.resetDetection };
}
