"""Tests for Sri Lankan fast-food reference lookup and glucose-aware meal guidance."""
from io import BytesIO
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.diet import router
from app.schemas.diet_schema import FoodDetectionResponse
from app.services import diet_service, fast_food_guidance_service


def mock_detections():
    items = [
        dict(class_id=22, food_name='Hoppers', confidence=0.85, bounding_box=dict(x1=0, y1=0, x2=40, y2=40)),
        dict(class_id=0, food_name='Basmati_Rice', confidence=0.90, bounding_box=dict(x1=45, y1=0, x2=90, y2=40)),
    ]
    return FoodDetectionResponse(
        detection_count=len(items),
        detections=items,
        image_width=100,
        image_height=100,
        model_name='YOLOv8n',
        confidence_threshold=0.25,
    )


class FastFoodGuidanceUnitTests(unittest.TestCase):
    def test_01_fast_food_csv_loads(self):
        foods = fast_food_guidance_service.all_foods()
        self.assertIsInstance(foods, dict)
        self.assertEqual(len(foods), 56)

    def test_02_unique_fast_food_id(self):
        foods = fast_food_guidance_service.all_foods().values()
        ids = [f['fast_food_id'] for f in foods]
        self.assertEqual(len(ids), len(set(ids)))

    def test_03_unique_food_name(self):
        foods = fast_food_guidance_service.all_foods().values()
        names = [f['food_name'] for f in foods]
        self.assertEqual(len(names), len(set(names)))

    def test_04_exact_food_lookup(self):
        g = fast_food_guidance_service.guidance_for('Hoppers', 100, 'mg/dL')
        self.assertTrue(g['is_fast_food'])
        self.assertTrue(g['guidance_available'])
        self.assertEqual(g['matched_food_name'], 'Hoppers')
        self.assertEqual(g['category'], 'Local Quick Meal')

    def test_05_unmatched_food_safe_fallback(self):
        g = fast_food_guidance_service.guidance_for('Basmati_Rice', 100, 'mg/dL')
        self.assertFalse(g['is_fast_food'])
        self.assertFalse(g['guidance_available'])
        self.assertIsNone(g['guidance_title'])
        self.assertIsNone(g['guidance_message'])
        self.assertIsNone(g['matched_food_name'])

    def test_06_mg_dl_handling(self):
        self.assertEqual(fast_food_guidance_service.normalize_glucose(100, 'mg/dL'), 100.0)
        self.assertEqual(fast_food_guidance_service.normalize_glucose('85.5', 'mg/dL'), 85.5)

    def test_07_mmol_l_to_mg_dl_conversion(self):
        # 5.0 mmol/L * 18 = 90.0 mg/dL
        self.assertEqual(fast_food_guidance_service.normalize_glucose(5.0, 'mmol/L'), 90.0)
        # 3.8 mmol/L * 18 = 68.4 mg/dL (< 70)
        self.assertAlmostEqual(fast_food_guidance_service.normalize_glucose(3.8, 'mmol/L'), 68.4)

    def test_08_glucose_below_70_is_low(self):
        state, mg = fast_food_guidance_service.glucose_state(69.9, 'mg/dL')
        self.assertEqual(state, 'low')
        self.assertAlmostEqual(mg, 69.9)

        # 3.5 mmol/L = 63.0 mg/dL -> low
        state_mmol, _ = fast_food_guidance_service.glucose_state(3.5, 'mmol/L')
        self.assertEqual(state_mmol, 'low')

    def test_09_glucose_70_or_above_is_not_low_when_no_high_threshold(self):
        # Without high_threshold_mg_dl configured, state must be 'not_low', never 'normal' or 'in range'
        state_70, _ = fast_food_guidance_service.glucose_state(70, 'mg/dL')
        self.assertEqual(state_70, 'not_low')

        state_180, _ = fast_food_guidance_service.glucose_state(180, 'mg/dL')
        self.assertEqual(state_180, 'not_low')

        state_300, _ = fast_food_guidance_service.glucose_state(300, 'mg/dL')
        self.assertEqual(state_300, 'not_low')

    def test_10_possible_fast_acting_carb_if_measured_behavior(self):
        # Soft_Drink_Regular has low_glucose_role = 'possible_fast_acting_carb_if_measured'
        g = fast_food_guidance_service.guidance_for('Soft_Drink_Regular', 60, 'mg/dL')
        self.assertEqual(g['glucose_state'], 'low')
        self.assertEqual(g['guidance_title'], 'Treat Low Glucose First')
        self.assertIn('fast-acting carbohydrate', g['guidance_message'])
        self.assertIn('measured portion', g['guidance_message'])

    def test_11_not_preferred_hypoglycemia_treatment_behavior(self):
        # Falooda has low_glucose_role = 'not_preferred_hypoglycemia_treatment'
        g = fast_food_guidance_service.guidance_for('Falooda', 60, 'mg/dL')
        self.assertEqual(g['glucose_state'], 'low')
        self.assertEqual(g['guidance_title'], 'Treat Low Glucose First')
        self.assertIn('not preferred for treating low glucose', g['guidance_message'])

    def test_12_not_hypoglycemia_treatment_behavior(self):
        # Chicken_Kottu has low_glucose_role = 'not_hypoglycemia_treatment'
        g = fast_food_guidance_service.guidance_for('Chicken_Kottu', 60, 'mg/dL')
        self.assertEqual(g['glucose_state'], 'low')
        self.assertEqual(g['guidance_title'], 'Treat Low Glucose First')
        self.assertIn('Treat the low glucose first', g['guidance_message'])
        self.assertIn('should not be used as the treatment', g['guidance_message'])

    def test_13_guidance_title_mapping(self):
        # Hoppers has general_action = 'portion_control' -> 'Watch Your Portion'
        g_hoppers = fast_food_guidance_service.guidance_for('Hoppers', 110, 'mg/dL')
        self.assertEqual(g_hoppers['guidance_title'], 'Watch Your Portion')

        # Pappadam has general_action = 'limit_or_modify' -> 'Choose Carefully'
        g_pappadam = fast_food_guidance_service.guidance_for('Pappadam', 110, 'mg/dL')
        self.assertEqual(g_pappadam['guidance_title'], 'Choose Carefully')

        # Kokis has general_action = 'avoid_or_rare' -> 'Best as an Occasional Choice'
        g_kokis = fast_food_guidance_service.guidance_for('Kokis', 110, 'mg/dL')
        self.assertEqual(g_kokis['guidance_title'], 'Best as an Occasional Choice')

    def test_14_blank_nutrition_remains_null(self):
        foods = fast_food_guidance_service.all_foods()
        kottu = foods['Chicken_Kottu']
        # In sri_lankan_fast_food_reference.csv, unmeasured entries have empty energy_kcal
        self.assertEqual(kottu['energy_kcal'].strip(), '')
        self.assertEqual(kottu['carbohydrates_g'].strip(), '')


class FastFoodApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router, prefix='/api')
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

        patcher = patch.object(diet_service, 'detect_food', return_value=mock_detections())
        self.model = patcher.start()
        self.addCleanup(patcher.stop)

        stream = BytesIO()
        Image.new('RGB', (100, 100)).save(stream, format='PNG')
        self.image = stream.getvalue()

    def test_15_analyze_meal_guidance_endpoint_response(self):
        response = self.client.post(
            '/api/diet/analyze-meal-guidance',
            files={'image': ('meal.png', self.image, 'image/png')},
            data={'current_glucose': '65', 'glucose_unit': 'mg/dL'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['detection_count'], 2)

    def test_16_current_glucose_included(self):
        response = self.client.post(
            '/api/diet/analyze-meal-guidance',
            files={'image': ('meal.png', self.image, 'image/png')},
            data={'current_glucose': '5.0', 'glucose_unit': 'mmol/L'},
        )
        self.assertEqual(response.status_code, 200)
        cg = response.json()['current_glucose']
        self.assertEqual(cg['value'], 5.0)
        self.assertEqual(cg['unit'], 'mmol/L')
        self.assertEqual(cg['normalized_mg_dl'], 90.0)
        self.assertEqual(cg['state'], 'not_low')

    def test_17_food_fast_food_guidance_included(self):
        response = self.client.post(
            '/api/diet/analyze-meal-guidance',
            files={'image': ('meal.png', self.image, 'image/png')},
            data={'current_glucose': '62', 'glucose_unit': 'mg/dL'},
        )
        self.assertEqual(response.status_code, 200)
        foods = {f['food_name']: f for f in response.json()['foods']}
        self.assertIn('Hoppers', foods)
        self.assertIn('Basmati_Rice', foods)

        # Matched food (Hoppers)
        h_guidance = foods['Hoppers']['fast_food_guidance']
        self.assertTrue(h_guidance['is_fast_food'])
        self.assertTrue(h_guidance['guidance_available'])
        self.assertEqual(h_guidance['guidance_title'], 'Treat Low Glucose First')

        # Unmatched food (Basmati_Rice)
        b_guidance = foods['Basmati_Rice']['fast_food_guidance']
        self.assertFalse(b_guidance['is_fast_food'])
        self.assertFalse(b_guidance['guidance_available'])
        self.assertIsNone(b_guidance['guidance_title'])

    def test_18_existing_endpoints_remain_unchanged(self):
        files = {'image': ('meal.png', self.image, 'image/png')}
        # detect-food
        r_det = self.client.post('/api/diet/detect-food', files=files)
        self.assertEqual(r_det.status_code, 200)

        # estimate-portions
        r_port = self.client.post('/api/diet/estimate-portions', files=files)
        self.assertEqual(r_port.status_code, 200)

        # map-nutrition
        r_nutr = self.client.post('/api/diet/map-nutrition', files=files)
        self.assertEqual(r_nutr.status_code, 200)

        # estimate-consumed-nutrition
        r_cons = self.client.post('/api/diet/estimate-consumed-nutrition', files=files)
        self.assertEqual(r_cons.status_code, 200)


if __name__ == '__main__':
    unittest.main()
