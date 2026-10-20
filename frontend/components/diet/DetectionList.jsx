import { Utensils } from 'lucide-react';
import { foodLabel, groupedPortionFoods } from '@/lib/diet-detection';
import styles from './food-detection.module.css';
import PortionEstimationResult from './PortionEstimationResult';
import NutritionMappingResult from './NutritionMappingResult';
import GlycemicIndexResult from './GlycemicIndexResult';
import GlycemicLoadResult from './GlycemicLoadResult';
import ConsumedNutritionResult from './ConsumedNutritionResult';
import AvailableCarbohydrateResult from './AvailableCarbohydrateResult';
import PersonalizedDietRecommendation from './PersonalizedDietRecommendation';

export default function DetectionList({ detections, summaries = [] }) {
  const foods = groupedPortionFoods(detections, summaries);
  return (
    <ol className={styles.detectionList}>
      {foods.map(food => {
        const guidance = food.fast_food_guidance;
        const details = guidance?.guidance_available === true
          ? [
              guidance.category,
              guidance.fried_food ? 'Fried' : null,
              guidance.sweetened_beverage ? 'Sweetened Drink' : null,
              guidance.dessert ? 'Dessert' : null,
            ].filter(Boolean)
          : [];

        return (
          <li key={food.food_name}>
            <div className={styles.resultTop}>
              <span className={styles.foodIcon}><Utensils size={19} /></span>
              <h4>{foodLabel(food.food_name)}</h4>
            </div>
            <PortionEstimationResult portion={food.portion} />
            {food.nutrition ? (
              <NutritionMappingResult nutrition={food.nutrition} />
            ) : (
              <section className={styles.nutritionPanel}>
                <h5 className={styles.consumedHeading}>Nutrition Information</h5>
                <p className={styles.nutritionEmpty}>Not available yet</p>
              </section>
            )}
            <GlycemicIndexResult gi={food.gi} />
            <GlycemicLoadResult value={food.glycemic_load} />
            <PersonalizedDietRecommendation recommendation={food.personalized_recommendation} />
            <AvailableCarbohydrateResult value={food.available_carbohydrate} />
            {food.consumed_nutrition && (
              <ConsumedNutritionResult
                servingWeight={food.serving_weight}
                consumed={food.consumed_nutrition}
              />
            )}
            {guidance?.guidance_available === true && (
              <section className={styles.guidancePanel} aria-label="Meal Guidance">
                <h5>Meal Guidance</h5>
                <strong>{guidance.guidance_title}</strong>
                <p>{guidance.guidance_message}</p>
                {details.length > 0 && <small>{details.join(' · ')}</small>}
              </section>
            )}
          </li>
        );
      })}
    </ol>
  );
}
