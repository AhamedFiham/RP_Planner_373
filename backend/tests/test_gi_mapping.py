"""Tests for Sri Lankan food Glycemic Index (GI) dataset and mapping service."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.diet import router
from app.schemas.diet_schema import FoodDetectionResponse
from app.services import diet_service, gi_mapping_service


def mock_detections():
    items = [
        dict(class_id=44, food_name='White_Rice', confidence=0.88, bounding_box=dict(x1=0, y1=0, x2=50, y2=50)),
        dict(class_id=9, food_name='Chicken_Curry', confidence=0.82, bounding_box=dict(x1=55, y1=0, x2=95, y2=50)),
    ]
    return FoodDetectionResponse(
        detection_count=len(items),
        detections=items,
        image_width=100,
        image_height=100,
        model_name='YOLOv8n',
        confidence_threshold=0.25,
    )


class GIMappingUnitTests(unittest.TestCase):
    def test_01_gi_csv_loads(self):
        catalog = gi_mapping_service.get_gi_catalog()
        self.assertIsInstance(catalog, dict)

    def test_02_exactly_46_rows(self):
        catalog = gi_mapping_service.get_gi_catalog()
        self.assertEqual(len(catalog), 46)

    def test_03_ids_0_to_45(self):
        catalog = gi_mapping_service.get_gi_catalog()
        class_ids = {cid for cid, _ in catalog.values()}
        self.assertEqual(class_ids, set(range(46)))

    def test_04_unique_food_names(self):
        catalog = gi_mapping_service.get_gi_catalog()
        self.assertEqual(len(set(catalog.keys())), 46)

    def test_05_exact_lookup(self):
        rec = gi_mapping_service.gi_for_food('White_Rice')
        self.assertIsNotNone(rec)
        self.assertEqual(rec.mapping_status, 'matched')
        self.assertEqual(rec.gi_value, 73.0)

    def test_06_matched_record(self):
        rec = gi_mapping_service.gi_for_food('White_Rice')
        self.assertEqual(rec.mapping_status, 'matched')
        self.assertEqual(rec.gi_value, 73.0)
        self.assertEqual(rec.gi_category, 'High')
        self.assertIsNotNone(rec.source_name)

    def test_07_representative_record(self):
        rec = gi_mapping_service.gi_for_food('Basmati_Rice')
        self.assertEqual(rec.mapping_status, 'representative')
        self.assertEqual(rec.gi_value, 58.0)
        self.assertEqual(rec.gi_category, 'Medium')
        self.assertIn('GI may vary', rec.notes or '')

    def test_08_candidate_record(self):
        rec = gi_mapping_service.gi_for_food('Hoppers')
        self.assertEqual(rec.mapping_status, 'candidate')
        self.assertEqual(rec.gi_value, 52.0)
        self.assertEqual(rec.gi_category, 'Low')

    def test_09_needs_source_record(self):
        rec = gi_mapping_service.gi_for_food('Chicken_Curry')
        self.assertEqual(rec.mapping_status, 'needs_source')
        self.assertIsNone(rec.gi_value)
        self.assertIsNone(rec.gi_category)
        self.assertIn('GI not established', rec.notes or '')

    def test_10_blank_gi_becomes_null(self):
        rec = gi_mapping_service.gi_for_food('Capsicum_Curry')
        self.assertIsNone(rec.gi_value)
        self.assertIsNone(rec.gi_category)
        self.assertEqual(rec.mapping_status, 'needs_source')

    def test_11_blank_gi_does_not_become_zero(self):
        rec = gi_mapping_service.gi_for_food('Chicken_Curry')
        self.assertIsNone(rec.gi_value)
        self.assertNotEqual(rec.gi_value, 0)
        self.assertNotEqual(rec.gi_value, 0.0)

    def test_12_gi_category_low(self):
        # Dhal_Curry is Low GI (<= 55)
        rec = gi_mapping_service.gi_for_food('Dhal_Curry')
        self.assertIsNotNone(rec.gi_value)
        self.assertLessEqual(rec.gi_value, 55.0)
        self.assertEqual(rec.gi_category, 'Low')

    def test_13_gi_category_medium(self):
        # Basmati_Rice is Medium GI (56 <= GI <= 69)
        rec = gi_mapping_service.gi_for_food('Basmati_Rice')
        self.assertIsNotNone(rec.gi_value)
        self.assertGreaterEqual(rec.gi_value, 56.0)
        self.assertLessEqual(rec.gi_value, 69.0)
        self.assertEqual(rec.gi_category, 'Medium')

    def test_14_gi_category_high(self):
        # White_Rice is High GI (>= 70)
        rec = gi_mapping_service.gi_for_food('White_Rice')
        self.assertIsNotNone(rec.gi_value)
        self.assertGreaterEqual(rec.gi_value, 70.0)
        self.assertEqual(rec.gi_category, 'High')

    def test_15_invalid_negative_gi_rejected(self):
        valid_csv = Path('datasets/diet/raw/diet_gi_46_classes.csv').read_text()
        # Replace White_Rice GI with negative number
        corrupt = valid_csv.replace('44,White_Rice,"Rice, white, boiled",73,High', '44,White_Rice,"Rice, white, boiled",-10,High')
        with tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False) as f:
            f.write(corrupt)
            f_path = Path(f.name)
        try:
            with self.assertRaises(gi_mapping_service.GIConfigurationError):
                gi_mapping_service.load_gi_reference(csv_path=f_path)
        finally:
            f_path.unlink(missing_ok=True)


class GIApiTests(unittest.TestCase):
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

    def test_16_map_gi_endpoint_works(self):
        response = self.client.post(
            '/api/diet/map-gi',
            files={'image': ('meal.png', self.image, 'image/png')},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['detection_count'], 2)
        foods = {f['food_name']: f for f in data['foods']}

        # White_Rice has matched High GI
        self.assertIn('White_Rice', foods)
        self.assertEqual(foods['White_Rice']['gi']['gi_value'], 73.0)
        self.assertEqual(foods['White_Rice']['gi']['gi_category'], 'High')
        self.assertEqual(foods['White_Rice']['gi']['mapping_status'], 'matched')

        # Chicken_Curry has null GI with needs_source
        self.assertIn('Chicken_Curry', foods)
        self.assertIsNone(foods['Chicken_Curry']['gi']['gi_value'])
        self.assertIsNone(foods['Chicken_Curry']['gi']['gi_category'])
        self.assertEqual(foods['Chicken_Curry']['gi']['mapping_status'], 'needs_source')

    def test_17_no_detection_returns_success_safely(self):
        self.model.return_value = mock_detections().model_copy(update={'detection_count': 0, 'detections': []})
        response = self.client.post(
            '/api/diet/map-gi',
            files={'image': ('meal.png', self.image, 'image/png')},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['detection_count'], 0)
        self.assertEqual(data['foods'], [])

    def test_18_existing_diet_endpoints_remain_unchanged(self):
        files = {'image': ('meal.png', self.image, 'image/png')}
        # detect-food
        self.assertEqual(self.client.post('/api/diet/detect-food', files=files).status_code, 200)
        # estimate-portions
        self.assertEqual(self.client.post('/api/diet/estimate-portions', files=files).status_code, 200)
        # map-nutrition
        self.assertEqual(self.client.post('/api/diet/map-nutrition', files=files).status_code, 200)
        # estimate-consumed-nutrition
        self.assertEqual(self.client.post('/api/diet/estimate-consumed-nutrition', files=files).status_code, 200)
        # analyze-meal-guidance with GI included in backward-compatible response
        guidance_resp = self.client.post(
            '/api/diet/analyze-meal-guidance',
            files=files,
            data={'current_glucose': '95', 'glucose_unit': 'mg/dL'},
        )
        self.assertEqual(guidance_resp.status_code, 200)
        guidance_data = guidance_resp.json()
        self.assertIn('current_glucose', guidance_data)
        # GI is attached to each food in guidance response
        self.assertIn('gi', guidance_data['foods'][0])


if __name__ == '__main__':
    unittest.main()
