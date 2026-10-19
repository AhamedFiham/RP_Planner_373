import { Utensils } from 'lucide-react';
import { foodLabel, groupedPortionFoods } from '@/lib/diet-detection';
import styles from './food-detection.module.css';
import PortionEstimationResult from './PortionEstimationResult';
import NutritionMappingResult from './NutritionMappingResult';
import ConsumedNutritionResult from './ConsumedNutritionResult';

export default function DetectionList({ detections, summaries = [] }) {
  const foods = groupedPortionFoods(detections, summaries);
  return <ol className={styles.detectionList}>{foods.map(food => <li key={food.food_name}>
    <div className={styles.resultTop}><span className={styles.foodIcon}><Utensils size={19}/></span><h4>{foodLabel(food.food_name)}</h4></div>
    <PortionEstimationResult portion={food.portion}/>
    {food.nutrition ? <NutritionMappingResult nutrition={food.nutrition}/> : <section className={styles.nutritionPanel}><h5 className={styles.consumedHeading}>Nutrition Information</h5><p className={styles.nutritionEmpty}>Not available yet</p></section>}
    {food.serving_weight && <ConsumedNutritionResult servingWeight={food.serving_weight} consumed={food.consumed_nutrition}/>}
  </li>)}</ol>;
}
