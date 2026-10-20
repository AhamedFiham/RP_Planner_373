"""Deterministic educational recommendations; deliberately independent of fast-food guidance."""
from app.schemas.diet_schema import PersonalizedDietRecommendation

def build_personalized_recommendation(glucose_state, food_name, portion, nutrition, consumed_nutrition, gi_result, gl_result):
    factors=[]; limitations=[]; category=getattr(portion,'portion_category',None) if portion else None
    if glucose_state: factors.append('current_glucose')
    if category: factors.append('portion')
    gi=getattr(gi_result,'gi_value',None) if gi_result else None
    gl=getattr(gl_result,'glycemic_load',None) if gl_result else None
    if gi is not None: factors.append('glycemic_index')
    if gl is not None: factors.append('glycemic_load')
    if nutrition is not None: factors.append('reference_nutrition')
    if consumed_nutrition is not None: factors.append('consumed_nutrition')
    if glucose_state=='low':
        return PersonalizedDietRecommendation(recommendation_title='Treat Low Glucose First',recommendation_message='Treat your low glucose first using a fast-acting carbohydrate according to your care plan. Review the meal after your glucose has been treated.',recommendation_level='low_glucose_priority',glucose_state=glucose_state,portion_action=None,alternative_suggestion=None,factors_used=factors,limitations=limitations)
    if gl is not None:
        if gl<=10: title,msg,level='Lower Glycemic Impact','This portion has a lower estimated glycemic load. Keep the portion balanced with vegetables, protein, and other foods appropriate to your meal plan.','informational'
        elif gl<20: title,msg,level='Watch Your Portion','This portion has a moderate estimated glycemic load. Consider keeping the portion controlled and balancing the meal with lower-carbohydrate foods.','portion_attention'
        else: title,msg,level='Consider a Smaller Portion','This portion has a higher estimated glycemic load. Consider a smaller portion where appropriate and balance the meal with foods lower in available carbohydrate.','higher_attention'
        return PersonalizedDietRecommendation(recommendation_title=title,recommendation_message=msg,recommendation_level=level,glucose_state=glucose_state,portion_action='Consider a smaller portion.' if category=='Large' else None,alternative_suggestion=None,factors_used=factors,limitations=limitations)
    if gi is not None:
        limitations.append('glycemic_load_unavailable'); limitations.append('serving_weight_unavailable')
        return PersonalizedDietRecommendation(recommendation_title='Portion Information Needed',recommendation_message='The Glycemic Index is available, but serving information is not sufficient to estimate the Glycemic Load for this portion.',recommendation_level='informational',glucose_state=glucose_state,portion_action=None,alternative_suggestion=None,factors_used=factors,limitations=limitations)
    limitations.extend(['gi_unavailable','glycemic_load_unavailable'])
    return PersonalizedDietRecommendation(recommendation_title='Limited Glycemic Information',recommendation_message='Not enough verified information is available to estimate the glycemic impact of this food. Use the available portion and nutrition information as general guidance.',recommendation_level='informational',glucose_state=glucose_state,portion_action=None,alternative_suggestion=None,factors_used=factors,limitations=limitations)
