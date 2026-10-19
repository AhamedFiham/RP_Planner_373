'use client';
import useDietDetection from './useDietDetection';
import { estimateMealPortions } from '@/lib/api';

export default function useDietPortionEstimation() {
  const state = useDietDetection(estimateMealPortions);
  return { ...state, estimatePortions: state.analyzeMeal, reset: state.resetDetection };
}
