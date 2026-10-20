import styles from './food-detection.module.css';
export default function PersonalizedDietRecommendation({recommendation}) {
 if(!recommendation) return null;
 return <section className={styles.guidancePanel} aria-label="Personalized Guidance"><h5>Personalized Guidance</h5><strong>{recommendation.recommendation_title}</strong><p>{recommendation.recommendation_message}</p>{recommendation.portion_action && <small>{recommendation.portion_action}</small>}</section>;
}
