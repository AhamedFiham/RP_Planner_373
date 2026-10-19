"""Read-only CSV validation/lookup and API integration; detection is mocked."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from app.api.diet import router
from app.schemas.diet_schema import FoodDetectionResponse
from app.services import diet_service
from app.services import nutrition_mapping_service as nutrition
from app.services.portion_estimation_service import estimate_from_detection


def response(name='Chicken_Curry',cid=9,duplicate=False):
    item=dict(class_id=cid,food_name=name,confidence=.81,bounding_box=dict(x1=0,y1=0,x2=30,y2=30))
    items=[item]
    if duplicate:items.append({**item,'bounding_box':dict(x1=40,y1=0,x2=70,y2=30)})
    return FoodDetectionResponse(detection_count=len(items),detections=items,image_width=100,image_height=100,model_name='YOLOv8n',confidence_threshold=.25)


class NutritionLookupTests(unittest.TestCase):
    def test_csv_taxonomy_and_exact_lookup(self):
        catalog=nutrition.load_nutrition_reference()
        self.assertEqual(len(catalog),46)
        self.assertEqual({cid for cid,_ in catalog.values()},set(range(46)))
        self.assertEqual(len(set(catalog)),46)
        with self.assertRaises(nutrition.NutritionConfigurationError):nutrition.nutrition_for_food('Chicken Curry')
        with self.assertRaises(nutrition.NutritionConfigurationError):nutrition.nutrition_for_food('Chicken_Curry',44)

    def test_matched_full_values_and_null_zero_distinction(self):
        n=nutrition.nutrition_for_food('Chicken_Curry',9)
        self.assertEqual(n.mapping_status,'matched_full')
        self.assertEqual(n.energy_kcal,123.82)
        self.assertEqual(n.carbohydrates_g,3.03)
        zero=nutrition.nutrition_for_food('Boiled_Eggs',4)
        self.assertEqual(zero.fiber_g,0)
        missing=nutrition.nutrition_for_food('Coconut_Sambol',11)
        self.assertIsNone(missing.vitamin_a_ug)
        self.assertIsNone(missing.calcium_mg)
        self.assertEqual(missing.mapping_status,'matched_macro')

    def test_serving_basis_not_converted(self):
        n=nutrition.nutrition_for_food('Lunu_Miris',27)
        self.assertEqual(n.mapping_status,'matched_serving')
        self.assertEqual(n.nutrition_basis,'per_serving')
        self.assertEqual(n.original_serving_quantity,10)
        self.assertEqual(n.original_serving_unit,'g')
        self.assertEqual(n.energy_kcal,12)
        self.assertEqual(n.original_energy_kcal,12)
        self.assertEqual(n.carbohydrates_g,1.43)
        self.assertEqual(n.data_completeness,'none')
        self.assertIsNone(n.energy_kj)

    def test_per_100g_basis_preserved(self):
        self.assertEqual(nutrition.nutrition_for_food('Basmati_Rice').nutrition_basis,'per_100g')

    def test_all_candidate_variants_have_warning(self):
        for food in ['White_Rice','Beetroot','Cucumber']:
            n=nutrition.nutrition_for_food(food)
            self.assertTrue(n.mapping_status.startswith('candidate_'))
            self.assertIn('manual confirmation',n.mapping_warning)
            self.assertIsNotNone(n.energy_kcal)

    def test_representative_warning(self):
        n=nutrition.nutrition_for_food('Dhal_Curry')
        self.assertEqual(n.mapping_status,'representative_full')
        self.assertIn('recipe variation',n.mapping_warning)

    def test_needs_source_is_null_not_failure(self):
        n=nutrition.nutrition_for_food('Capsicum_Curry')
        self.assertEqual(n.mapping_status,'needs_source')
        self.assertEqual(n.data_completeness,'none')
        self.assertIsNone(n.nutrition_basis)
        self.assertTrue(all(getattr(n,field) is None for field in nutrition.NUTRITION_NUMERIC_FIELDS))

    def test_original_servings_and_metadata_preserved(self):
        n=nutrition.nutrition_for_food('Pappadam')
        self.assertEqual(n.original_serving_quantity,7)
        self.assertEqual(n.original_serving_unit,'g')
        self.assertEqual(n.original_proteins_g,1)
        self.assertIsNotNone(n.supplemental_source)
        self.assertIsNotNone(n.source_food_name)
        self.assertIsNotNone(n.notes)

    def test_source_anomaly_flagged_not_changed(self):
        n=nutrition.nutrition_for_food('Shrimp_Curry')
        self.assertEqual(n.water_g,109.37)
        self.assertTrue(n.data_quality_warnings)

    def test_cache_once_including_concurrent_first_load(self):
        previous=nutrition._catalog;nutrition._catalog=None
        try:
            with patch.object(nutrition,'load_nutrition_reference',wraps=nutrition.load_nutrition_reference) as loader:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    catalogs=list(pool.map(lambda _:nutrition.get_nutrition_catalog(),range(4)))
                nutrition.nutrition_for_food('Chicken_Curry')
                self.assertEqual(loader.call_count,1)
                self.assertTrue(all(c is catalogs[0] for c in catalogs))
        finally:nutrition._catalog=previous

    def test_lookup_copies_prevent_cache_mutation(self):
        n=nutrition.nutrition_for_food('Chicken_Curry');n.energy_kcal=0
        self.assertEqual(nutrition.nutrition_for_food('Chicken_Curry').energy_kcal,123.82)

    def test_missing_csv(self):
        with self.assertRaises(nutrition.NutritionConfigurationError):nutrition.load_nutrition_reference(Path('/tmp/no-such-nutrition-file.csv'))

    def test_malformed_shapes_values_and_taxonomy_fail(self):
        with nutrition.CSV_PATH.open(encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle);headers=reader.fieldnames;original=list(reader)
        cases=[]
        cases.append((headers,original[:-1]))
        duplicate=[dict(row) for row in original];duplicate[1]['class_id']='0';cases.append((headers,duplicate))
        wrong=[dict(row) for row in original];wrong[1]['food_name']='Chicken Curry';cases.append((headers,wrong))
        duplicate_name=[dict(row) for row in original];duplicate_name[1]['food_name']=duplicate_name[0]['food_name'];cases.append((headers,duplicate_name))
        bad=[dict(row) for row in original];bad[0]['energy_kcal']='nan';cases.append((headers,bad))
        cases.append(([h for h in headers if h!='energy_kcal'],original))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.csv'
            for fields,rows in cases:
                with path.open('w',newline='') as handle:
                    writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
                with self.assertRaises(nutrition.NutritionConfigurationError):nutrition.load_nutrition_reference(path)
            path.write_text('garbage\nnot a CSV\n')
            with self.assertRaises(nutrition.NutritionConfigurationError):nutrition.load_nutrition_reference(path)


class NutritionApiTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(router,prefix='/api');self.client=TestClient(app);self.addCleanup(self.client.close)
        self.detector_patch=patch.object(diet_service,'detect_food',return_value=response());self.detector=self.detector_patch.start();self.addCleanup(self.detector_patch.stop)
        stream=BytesIO();Image.new('RGB',(100,100)).save(stream,format='PNG');self.image=stream.getvalue()

    def upload(self,route='/api/diet/map-nutrition',name='meal.png',data=None,mime='image/png'):
        return self.client.post(route,files={'image':(name,self.image if data is None else data,mime)})

    def test_endpoint_maps_once_and_preserves_summary(self):
        self.detector.return_value=response(duplicate=True)
        expected=estimate_from_detection(self.detector.return_value)
        r=self.upload();self.assertEqual(r.status_code,200)
        payload=r.json();self.assertEqual(payload['portion_summary'],expected.model_dump()['portion_summary'])
        self.assertEqual(payload['foods'][0]['nutrition'],payload['foods'][1]['nutrition'])
        self.assertEqual(payload['foods'][0]['nutrition']['energy_kcal'],123.82)
        self.assertEqual(payload['foods'][0]['portion']['estimated_grams'],None)
        self.assertEqual(payload['detection_count'],2)
        self.detector.assert_called_once()
        self.assertNotIn('total',payload)

    def test_older_endpoints_unchanged(self):
        self.assertEqual(self.upload('/api/diet/detect-food').json(),self.detector.return_value.model_dump())
        self.assertEqual(self.upload('/api/diet/estimate-portions').json(),estimate_from_detection(self.detector.return_value).model_dump())

    def test_no_detections(self):
        self.detector.return_value=response().model_copy(update={'detection_count':0,'detections':[]})
        r=self.upload();self.assertEqual(r.status_code,200);self.assertEqual(r.json()['foods'],[]);self.assertEqual(r.json()['portion_summary'],[])

    def test_unavailable_reference_not_404(self):
        self.detector.return_value=response('Capsicum_Curry',6)
        r=self.upload();self.assertEqual(r.status_code,200)
        self.assertIsNone(r.json()['foods'][0]['nutrition']['energy_kcal'])

    def test_candidate_and_serving_record(self):
        self.detector.return_value=response('Cucumber',12)
        n=self.upload().json()['foods'][0]['nutrition']
        self.assertEqual(n['nutrition_basis'],'per_serving');self.assertEqual(n['original_serving_quantity'],50)
        self.assertIn('Candidate',n['mapping_warning'])

    def test_bad_images(self):
        for data in [b'',b'corrupt']:
            with self.subTest(data=data):self.assertEqual(self.upload(data=data).status_code,400)
        self.assertEqual(self.upload(name='meal.txt',mime='text/plain').status_code,400)
        self.assertEqual(self.client.post('/api/diet/map-nutrition').status_code,400)

    def test_inference_failure(self):
        self.detector.side_effect=diet_service.DietDetectionError('private path')
        r=self.upload();self.assertEqual(r.status_code,500);self.assertNotIn('private path',r.text)

    def test_nutrition_config_failure_sanitized(self):
        with patch.object(nutrition,'get_nutrition_catalog',side_effect=nutrition.NutritionConfigurationError(str(nutrition.CSV_PATH))):r=self.upload()
        self.assertEqual(r.status_code,500)
        self.assertNotIn(str(nutrition.CSV_PATH),r.text)

    def test_main_app_registration(self):
        from app.main import app
        with TestClient(app) as client:self.assertIn('/api/diet/map-nutrition',client.get('/openapi.json').json()['paths'])


if __name__=='__main__':unittest.main()
