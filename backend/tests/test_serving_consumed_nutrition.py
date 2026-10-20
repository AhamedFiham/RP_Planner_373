"""Serving/consumption formulas use synthetic TEST-ONLY source records, not real weights."""
import copy
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from app.api.diet import router
from app.schemas.diet_schema import FoodDetectionResponse, NutritionReference, ServingWeightEstimate
from app.services import serving_weight_service as serving
from app.services import consumed_nutrition_service as consumed
from app.services import diet_service
from app.services.nutrition_mapping_service import map_nutrition
from app.services.portion_estimation_service import estimate_from_detection


def fixture_entry(method='portion_category',**kwargs):
    # These arbitrary test masses are mathematical fixtures, never written to production config.
    return dict(serving_method=method,small_g=None,medium_g=None,large_g=None,grams_per_unit=None,reference_serving_g=None,
        source_name='TEST ONLY: synthetic fixture',source_reference='TEST ONLY: not a serving recommendation',validation_notes='TEST ONLY: formula validation fixture',
        validated=True,status='available',reference_match_confirmed=False,matching_portion_category=None,nutrition_mapping_confirmed=False,**kwargs)


def weight(value=50):return ServingWeightEstimate(serving_method='portion_category',estimated_serving_weight_g=value,
    serving_weight_status='available',validated=True,source_name='TEST ONLY',source_reference='TEST ONLY')


def reference(**kwargs):
    values=dict(nutrition_basis='per_100g',mapping_status='matched_full',data_completeness='full_macro_micro',energy_kcal=120,energy_kj=500,carbohydrates_g=20,proteins_g=5,fat_g=0,fiber_g=None)
    values.update(kwargs);return NutritionReference(**values)


def detection_response(duplicate=False):
    items=[dict(class_id=9,food_name='Chicken_Curry',confidence=.8,bounding_box=dict(x1=0,y1=0,x2=30,y2=30))]
    if duplicate:items.append({**items[0],'confidence':.9,'bounding_box':dict(x1=40,y1=0,x2=70,y2=30)})
    return FoodDetectionResponse(detection_count=len(items),detections=items,image_width=100,image_height=100,model_name='YOLOv8n',confidence_threshold=.25)


class ServingWeightTests(unittest.TestCase):
    def test_config_46_exact_foods_all_unavailable(self):
        config=serving.load_serving_weights()
        names=json.loads(Path('trained_models/diet/class_names.json').read_text())
        self.assertEqual(set(config['foods']),set(names.values()))
        self.assertEqual(len(config['foods']),46)
        self.assertEqual(config['foods']['Hoppers']['status'],'available')
        self.assertTrue(config['foods']['Hoppers']['validated'])
        self.assertEqual(config['foods']['Hoppers']['grams_per_unit'],25)
        self.assertTrue(config['foods']['String_Hoppers']['validated'])
        self.assertTrue(config['foods']['White_Rice']['validated'])
        self.assertFalse(config['foods']['Pappadam']['validated'])
        self.assertFalse(config['foods']['Boiled_Eggs']['validated'])
        self.assertEqual(config['foods']['White_Rice']['small_g'],100)
        self.assertEqual(config['foods']['White_Rice']['medium_g'],150)
        self.assertEqual(config['foods']['White_Rice']['large_g'],200)
        self.assertEqual(config['foods']['Pappadam']['grams_per_unit'],10)
        self.assertEqual(config['foods']['Boiled_Eggs']['grams_per_unit'],90)
        self.assertIsNone(config['foods']['Kottu']['small_g'])
        self.assertIsNone(config['foods']['Dhal_Curry']['small_g'])

    def test_exact_lookup_and_missing_weight(self):
        result=serving.estimate_serving_weight('White_Rice','Medium')
        self.assertIsNone(result.estimated_serving_weight_g);self.assertEqual(result.serving_weight_status,'portion_unknown')
        unknown=serving.estimate_serving_weight('White Rice','Medium')
        self.assertEqual(unknown.serving_method,'unsupported');self.assertIsNone(unknown.estimated_serving_weight_g)

    def test_category_lookup_only_explicit_sourced_values(self):
        entry=fixture_entry();entry.update(small_g=25,medium_g=50,large_g=75)
        with patch.object(serving,'get_serving_weights',return_value={'foods':{'White_Rice':entry}}):
            for category,expected in [('Small',25),('Medium',50),('Large',75),('Unknown',None)]:
                self.assertEqual(serving.estimate_serving_weight('White_Rice',category).estimated_serving_weight_g,expected)

    def test_count_based_weight_and_ambiguity(self):
        entry=fixture_entry('count_based');entry['grams_per_unit']=25
        with patch.object(serving,'get_serving_weights',return_value={'foods':{'Cutlet':entry}}):
            self.assertEqual(serving.estimate_serving_weight('Cutlet','Medium',2).estimated_serving_weight_g,50)
            for count in [None,0,True]:self.assertIsNone(serving.estimate_serving_weight('Cutlet','Medium',count).estimated_serving_weight_g)
            self.assertIsNone(serving.estimate_serving_weight('Cutlet','Medium',2,count_ambiguous=True).estimated_serving_weight_g)

    def test_reference_serving_requires_explicit_match(self):
        entry=fixture_entry('reference_serving');entry.update(reference_serving_g=10,reference_match_confirmed=True,matching_portion_category='Small')
        with patch.object(serving,'get_serving_weights',return_value={'foods':{'Lunu_Miris':entry}}):
            self.assertEqual(serving.estimate_serving_weight('Lunu_Miris','Small').estimated_serving_weight_g,10)
            self.assertIsNone(serving.estimate_serving_weight('Lunu_Miris','Large').estimated_serving_weight_g)

    def test_source_quantities_not_promoted_to_weights(self):
        for name in ['Lunu_Miris','Pappadam','Cucumber']:
            self.assertIsNone(serving.estimate_serving_weight(name,'Medium',2).estimated_serving_weight_g)

    def test_cache_loads_once(self):
        previous=serving._reference;serving._reference=None
        try:
            with patch.object(serving,'load_serving_weights',wraps=serving.load_serving_weights) as loader:
                with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:serving.get_serving_weights(),range(4)))
                self.assertEqual(loader.call_count,1)
        finally:serving._reference=previous

    def test_config_rejects_missing_food_invalid_unsupported_mass_and_missing_evidence(self):
        config=serving.load_serving_weights();cases=[]
        missing=copy.deepcopy(config);del missing['foods']['White_Rice'];cases.append(missing)
        for value in [-1,0,float('nan')]:
            bad=copy.deepcopy(config);bad['foods']['White_Rice']['medium_g']=value;cases.append(bad)
        unsourced=copy.deepcopy(config);unsourced['foods']['White_Rice']['medium_g']=50;cases.append(unsourced)
        wrong=copy.deepcopy(config);wrong['foods']['White_Rice']['serving_method']='fake';cases.append(wrong)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'weights.json'
            for value in cases:
                path.write_text(json.dumps(value))
                with self.assertRaises(serving.ServingWeightConfigurationError):serving.load_serving_weights(path)
            path.write_text('broken')
            with self.assertRaises(serving.ServingWeightConfigurationError):serving.load_serving_weights(path)
            with self.assertRaises(serving.ServingWeightConfigurationError):serving.load_serving_weights(Path(folder)/'missing.json')

    def test_sourced_fixture_validates_but_is_not_saved(self):
        config=serving.load_serving_weights();config['foods']['White_Rice']=fixture_entry();config['foods']['White_Rice']['medium_g']=50
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'weights.json';path.write_text(json.dumps(config))
            self.assertEqual(serving.load_serving_weights(path)['foods']['White_Rice']['medium_g'],50)


class ConsumedFormulaTests(unittest.TestCase):
    def test_per_100g_formula_and_null_zero_safety(self):
        result,status=consumed.calculate_consumed_nutrition(reference(),weight())
        self.assertEqual(status,'estimated');self.assertEqual(result.energy_kcal,60);self.assertEqual(result.carbohydrates_g,10)
        self.assertEqual(result.proteins_g,2.5);self.assertEqual(result.fat_g,0);self.assertIsNone(result.fiber_g)
        self.assertEqual(result.energy_kj,250)

    def test_per_serving_known_grams_approximation(self):
        n=reference(nutrition_basis='per_serving',original_serving_quantity=10,original_serving_unit='g')
        result,status=consumed.calculate_consumed_nutrition(n,weight(20))
        self.assertEqual(result.energy_kcal,240)
        self.assertEqual(result.scaling_factor,2)
        self.assertEqual(result.calculation_basis,'per_serving_gram_scaling_approximation')
        self.assertTrue(any('approximation' in note for note in result.notes))

    def test_exact_one_reference_serving_uses_factor_one(self):
        n=reference(nutrition_basis='per_serving',original_serving_quantity=10,original_serving_unit='g')
        result,_=consumed.calculate_consumed_nutrition(n,weight(10))
        self.assertEqual(result.energy_kcal,n.energy_kcal);self.assertEqual(result.scaling_factor,1)

    def test_unscalable_serving_basis(self):
        for quantity,unit in [(None,'g'),(0,'g'),(10,None),(10,'piece')]:
            out,status=consumed.calculate_consumed_nutrition(reference(nutrition_basis='per_serving',original_serving_quantity=quantity,original_serving_unit=unit),weight())
            self.assertIsNone(out);self.assertEqual(status,'nutrition_basis_not_scalable')

    def test_absent_weight_or_source_means_null(self):
        unavailable=ServingWeightEstimate(serving_method='portion_category',serving_weight_status='needs_reference')
        self.assertIsNone(consumed.calculate_consumed_nutrition(reference(),unavailable)[0])
        unproven=weight();unproven.source_name=None
        self.assertIsNone(consumed.calculate_consumed_nutrition(reference(),unproven)[0])

    def test_unavailable_or_unconfirmed_nutrition(self):
        self.assertIsNone(consumed.calculate_consumed_nutrition(reference(mapping_status='needs_source'),weight())[0])
        for status in ['candidate_macro','representative_full']:
            self.assertIsNone(consumed.calculate_consumed_nutrition(reference(mapping_status=status),weight())[0])
            confirmed=weight();confirmed.nutrition_mapping_confirmed=True
            self.assertIsNotNone(consumed.calculate_consumed_nutrition(reference(mapping_status=status),confirmed)[0])

    def test_grouped_foods_once_no_totals(self):
        mapped=map_nutrition(estimate_from_detection(detection_response(True)))
        out=consumed.estimate_consumed_nutrition(mapped)
        self.assertEqual(len(out.foods),1);self.assertEqual(len(out.detections),2)
        self.assertEqual(out.foods[0].detection_indices,[0,1]);self.assertEqual(out.foods[0].confidence,.9)
        self.assertIsNone(out.foods[0].consumed_nutrition)
        self.assertNotIn('total',out.model_dump())


class ConsumedApiTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(router,prefix='/api');self.client=TestClient(app);self.addCleanup(self.client.close)
        patcher=patch.object(diet_service,'detect_food',return_value=detection_response(True));self.model=patcher.start();self.addCleanup(patcher.stop)
        stream=BytesIO();Image.new('RGB',(100,100)).save(stream,format='PNG');self.image=stream.getvalue()

    def request(self,path='/api/diet/estimate-consumed-nutrition',data=None):return self.client.post(path,files={'image':('meal.png',self.image if data is None else data,'image/png')})

    def test_new_endpoint_grouped_nulls_and_one_detection_pass(self):
        r=self.request();self.assertEqual(r.status_code,200)
        out=r.json();self.assertEqual(out['detection_count'],2);self.assertEqual(len(out['foods']),1)
        self.assertIsNone(out['foods'][0]['consumed_nutrition']);self.assertEqual(out['foods'][0]['serving_weight']['serving_weight_status'],'needs_reference')
        self.assertIsNone(out['foods'][0]['serving_weight']['estimated_serving_weight_g'])
        self.assertEqual(len(out['detections']),2);self.model.assert_called_once()

    def test_older_endpoints_unchanged(self):
        expected=self.model.return_value
        self.assertEqual(self.request('/api/diet/detect-food').json(),expected.model_dump())
        self.assertEqual(self.request('/api/diet/estimate-portions').json(),estimate_from_detection(expected).model_dump())
        self.assertEqual(self.request('/api/diet/map-nutrition').json(),map_nutrition(estimate_from_detection(expected)).model_dump())

    def test_empty_results(self):
        self.model.return_value=detection_response().model_copy(update={'detection_count':0,'detections':[]})
        r=self.request();self.assertEqual(r.status_code,200);self.assertEqual(r.json()['foods'],[])

    def test_errors_sanitized(self):
        self.assertEqual(self.request(data=b'broken').status_code,400)
        with patch.object(serving,'get_serving_weights',side_effect=serving.ServingWeightConfigurationError('private/path')):
            r=self.request();self.assertEqual(r.status_code,500);self.assertNotIn('private/path',r.text)

    def test_main_app_route(self):
        from app.main import app
        with TestClient(app) as client:self.assertIn('/api/diet/estimate-consumed-nutrition',client.get('/openapi.json').json()['paths'])


if __name__=='__main__':unittest.main()
