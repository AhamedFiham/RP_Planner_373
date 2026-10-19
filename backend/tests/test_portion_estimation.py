"""V1 geometry/config tests and API tests with mocked existing detection."""
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError
from app.api.diet import router
from app.schemas.diet_schema import FoodDetectionResponse, PortionEstimate
from app.services import diet_service
from app.services import portion_estimation_service as portion


def detection(name='White_Rice',cid=44,box=(0,0,50,50)):
    return dict(class_id=cid,food_name=name,confidence=.9,bounding_box=dict(zip(('x1','y1','x2','y2'),box)))


def estimate(rows):return portion.estimate_portions(rows,100,100)


class PortionServiceTests(unittest.TestCase):
    def test_relative_area(self):
        out=estimate([detection(box=(10,20,60,70))])
        self.assertAlmostEqual(out.foods[0].portion.relative_area,.25)
        self.assertEqual(out.foods[0].portion.portion_category,portion.category(.25,portion.load_portion_reference()['foods']['White_Rice']))
        self.assertIsNone(out.foods[0].portion.estimated_grams)

    def test_invalid_boxes(self):
        for box in [(-1,0,50,50),(50,0,1,50),(0,5,50,5),(0,0,101,50),(0,0,float('nan'),50)]:
            with self.subTest(box=box),self.assertRaises(ValueError):estimate([detection(box=box)])

    def test_invalid_dimensions(self):
        for width,height in [(0,100),(100,0),(-1,100),(100,-1),(float('nan'),100),(True,100)]:
            with self.subTest(width=width,height=height),self.assertRaises(ValueError):portion.estimate_portions([],width,height)

    def test_full_image_area_stays_in_range(self):
        result=estimate([detection(box=(0,0,100,100)) for _ in range(3)])
        self.assertEqual(result.portion_summary[0].relative_area,1)

    def test_disjoint_same_food_areas_sum(self):
        out=estimate([detection(box=(0,0,20,50)),detection(box=(40,0,60,50))])
        self.assertEqual(len(out.foods),2)
        self.assertEqual(len(out.portion_summary),1)
        self.assertAlmostEqual(out.portion_summary[0].relative_area,.2)

    def test_overlapping_area_union_not_double_counted(self):
        out=estimate([detection(box=(0,0,50,50)),detection(box=(25,0,75,50))])
        self.assertAlmostEqual(out.portion_summary[0].relative_area,.375)

    def test_nested_area_union(self):
        out=estimate([detection(box=(0,0,100,100)),detection(box=(5,5,20,20))])
        self.assertEqual(out.portion_summary[0].relative_area,1)

    def test_count_grouping(self):
        out=estimate([detection('Cutlet',13,(0,0,20,20)),detection('Cutlet',13,(30,0,50,20))])
        summary=out.portion_summary[0]
        self.assertEqual(summary.count,2)
        self.assertEqual(summary.portion_category,'Medium')
        self.assertTrue(all(d.portion.count is None for d in out.foods))
        self.assertFalse(summary.validated)

    def test_overlapping_count_is_ambiguous(self):
        out=estimate([detection('Cutlet',13,(0,0,30,30)),detection('Cutlet',13,(20,0,50,30))])
        summary=out.portion_summary[0]
        self.assertIsNone(summary.count)
        self.assertTrue(summary.count_ambiguous)
        self.assertEqual(summary.portion_category,'Unknown')
        self.assertEqual(summary.observed_detection_count,2)

    def test_identical_boxes_do_not_invent_count(self):
        summary=estimate([detection('Cutlet',13)]*2).portion_summary[0]
        self.assertIsNone(summary.count)

    def test_unknown_food_falls_back(self):
        out=estimate([detection('Unlisted_Food')])
        self.assertEqual(out.foods[0].portion.method,'reference_based')
        self.assertEqual(out.foods[0].portion.portion_category,'Unknown')

    def test_missing_config_entry_falls_back(self):
        config=portion.load_portion_reference()
        del config['foods']['White_Rice']
        with patch.object(portion,'load_portion_reference',return_value=config):
            self.assertEqual(estimate([detection()]).portion_summary[0].method,'reference_based')

    def test_reference_bundles_not_counted(self):
        out=estimate([detection('String_Hoppers',40)])
        self.assertEqual(out.portion_summary[0].method,'reference_based')
        self.assertIsNone(out.portion_summary[0].count)

    def test_config_covers_packaged_taxonomy(self):
        config=portion.load_portion_reference()
        names=json.loads(Path('trained_models/diet/class_names.json').read_text())
        self.assertEqual(set(names.values()),set(config['foods']))
        self.assertTrue(all(e['serving_weights'] is None and not e['validated'] for e in config['foods'].values()))
        self.assertTrue(all(e['portion_rules'] is not None for e in config['foods'].values() if e['method']!='reference_based'))

    def test_missing_or_corrupt_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rules.json'
            with self.assertRaises(portion.PortionConfigurationError):portion.load_portion_reference(path)
            path.write_text('not JSON')
            with self.assertRaises(portion.PortionConfigurationError):portion.load_portion_reference(path)

    def test_unsupported_gram_config_rejected(self):
        config=portion.load_portion_reference()
        config['foods']['White_Rice']['serving_weights']={'Medium':100}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rules.json';path.write_text(json.dumps(config))
            with self.assertRaises(portion.PortionConfigurationError):portion.load_portion_reference(path)

    def test_explicit_provisional_rules_only(self):
        for method,food,rows,rules in [
            ('count_based','Cutlet',[detection('Cutlet',13,(0,0,20,20)),detection('Cutlet',13,(30,0,50,20))],{'small_max_count':1,'medium_max_count':2}),
            ('area_based','White_Rice',[detection()],{'small_max_relative_area':.1,'medium_max_relative_area':.3})]:
            config=portion.load_portion_reference()
            entry=config['foods'][food];entry.update(portion_rules=rules,threshold_source='research_baseline_provisional')
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'rules.json';path.write_text(json.dumps(config))
                with patch.object(portion,'REFERENCE_PATH',path):
                    out=estimate(rows)
                self.assertEqual(out.portion_summary[0].portion_category,'Medium')
                self.assertFalse(out.portion_summary[0].validated)
                self.assertIsNone(out.portion_summary[0].estimated_grams)

    def test_all_methods_have_no_grams(self):
        out=estimate([detection(),detection('Cutlet',13),detection('String_Hoppers',40)])
        self.assertTrue(all(d.portion.estimated_grams is None for d in out.foods))
        with self.assertRaises(ValidationError):PortionEstimate(method='area_based',portion_category='Small',estimated_grams=100)

    def test_inconsistent_class_names_rejected(self):
        with self.assertRaises(ValueError):estimate([detection(),detection('Something_Else')])


class PortionApiTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(router,prefix='/api')
        self.client=TestClient(app);self.addCleanup(self.client.close)
        self.response=FoodDetectionResponse(detection_count=1,detections=[detection()],image_width=100,image_height=100,model_name='YOLOv8n',confidence_threshold=.25)
        self.mock=patch.object(diet_service,'detect_food',return_value=self.response).start()
        self.addCleanup(patch.stopall)
        stream=BytesIO();Image.new('RGB',(100,100)).save(stream,format='PNG');self.bytes=stream.getvalue()

    def upload(self,url='/api/diet/estimate-portions',name='meal.png',data=None,mime='image/png'):
        return self.client.post(url,files={'image':(name,self.bytes if data is None else data,mime)})

    def test_main_app_registers_portion_route(self):
        from app.main import app
        with TestClient(app) as client:
            paths=client.get('/openapi.json').json()['paths']
        self.assertIn('post',paths['/api/diet/estimate-portions'])

    def test_response_structure(self):
        response=self.upload();self.assertEqual(response.status_code,200)
        data=response.json();self.assertEqual(data['detection_count'],1)
        self.assertEqual(data['foods'][0]['portion']['method'],'area_based')
        self.assertEqual(data['foods'][0]['portion']['relative_area'],.25)
        self.assertEqual(data['portion_summary'][0]['food_name'],'White_Rice')
        self.assertIsNone(data['foods'][0]['portion']['estimated_grams'])
        self.mock.assert_called_once()

    def test_detection_endpoint_unchanged(self):
        response=self.upload('/api/diet/detect-food')
        self.assertEqual(response.json(),self.response.model_dump())
        self.assertNotIn('portion_summary',response.json())

    def test_no_detections(self):
        self.mock.return_value=self.response.model_copy(update={'detection_count':0,'detections':[]})
        response=self.upload();self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['foods'],[])
        self.assertEqual(response.json()['portion_summary'],[])

    def test_invalid_image(self):self.assertEqual(self.upload(data=b'broken').status_code,400)
    def test_empty_image(self):self.assertEqual(self.upload(data=b'').status_code,400)
    def test_unsupported_file(self):self.assertEqual(self.upload(name='meal.txt',mime='text/plain').status_code,400)
    def test_missing_image(self):self.assertEqual(self.client.post('/api/diet/estimate-portions').status_code,400)

    def test_inference_failure(self):
        self.mock.side_effect=diet_service.DietDetectionError('private/path')
        response=self.upload();self.assertEqual(response.status_code,500)
        self.assertNotIn('private/path',response.text)

    def test_config_failure_is_sanitized(self):
        with patch.object(portion,'load_portion_reference',side_effect=portion.PortionConfigurationError('private/path')):
            response=self.upload()
        self.assertEqual(response.status_code,500)
        self.assertNotIn('private/path',response.text)


if __name__=='__main__':unittest.main()
