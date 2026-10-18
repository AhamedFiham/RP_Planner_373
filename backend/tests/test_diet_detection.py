"""Focused API tests mock prediction; one test loads the actual model once."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from app.api.diet import router
from app.models.diet_model import DietDetector
from app.services import diet_service as service
os.environ.setdefault('YOLO_CONFIG_DIR', str(service.BACKEND/'outputs/diet/.ultralytics'))
os.environ.setdefault('MPLCONFIGDIR', str(service.BACKEND/'outputs/diet/.matplotlib'))


def image_bytes(format='PNG'):
    stream = BytesIO()
    Image.new('RGB',(100,80),'white').save(stream,format=format)
    return stream.getvalue()


def result(rows):
    data = Mock()
    data.detach.return_value = data
    data.cpu.return_value = data
    data.tolist.return_value = rows
    return [SimpleNamespace(boxes=SimpleNamespace(data=data))]


class DietApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router,prefix='/api')
        self.client = TestClient(app)
        names = {0:'Basmati_Rice',44:'White_Rice'}
        self.model = Mock()
        self.model.predict.return_value = result([[1,2,90,70,.7,44],[3,4,50,60,.9,0]])
        detector = DietDetector(self.model,names,dict(selected_model='YOLOv8n',input_image_size=640,
            dataset_version='training_v3',class_count=46))
        self.patcher = patch.object(service,'get_detector',return_value=detector)
        self.patcher.start()
        self.env = patch.dict(os.environ,{'DIET_DETECTION_CONFIDENCE':'.25'})
        self.env.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.env.stop)
        self.addCleanup(self.client.close)

    def upload(self,name='meal.png',data=None,mime='image/png'):
        return self.client.post('/api/diet/detect-food',files={'image':(name,image_bytes() if data is None else data,mime)})

    def test_valid_response_sorted_and_fields(self):
        response = self.upload()
        self.assertEqual(response.status_code,200)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['detection_count'],2)
        self.assertEqual((body['image_width'],body['image_height']),(100,80))
        self.assertEqual([d['confidence'] for d in body['detections']],[.9,.7])
        for detection in body['detections']:
            self.assertEqual(set(detection),{'class_id','food_name','confidence','bounding_box'})
            self.assertTrue(0<=detection['confidence']<=1)
            box=detection['bounding_box']
            self.assertTrue(0<=box['x1']<box['x2']<=100)
            self.assertTrue(0<=box['y1']<box['y2']<=80)
        options = self.model.predict.call_args.kwargs
        self.assertEqual(options['conf'],.25)
        self.assertFalse(options['save'])

    def test_supported_formats(self):
        for suffix,mime,fmt in [('jpg','image/jpeg','JPEG'),('jpeg','image/jpeg','JPEG'),('png','image/png','PNG'),('webp','image/webp','WEBP')]:
            with self.subTest(suffix=suffix):
                self.assertEqual(self.upload('meal.'+suffix,image_bytes(fmt),mime).status_code,200)

    def test_missing_image(self):
        self.assertEqual(self.client.post('/api/diet/detect-food').status_code,400)

    def test_blank_filename(self):
        self.assertEqual(self.upload(' ').status_code,400)

    def test_missing_filename(self):
        self.assertEqual(self.upload('',b'abc').status_code,400)

    def test_unsupported_file(self):
        self.assertEqual(self.upload('file.txt',b'text','text/plain').status_code,400)

    def test_wrong_mime(self):
        self.assertEqual(self.upload(mime='application/octet-stream').status_code,400)

    def test_content_extension_mismatch(self):
        self.assertEqual(self.upload('meal.jpg',mime='image/jpeg').status_code,400)

    def test_empty_file(self):
        self.assertEqual(self.upload(data=b'').status_code,400)
        self.model.predict.assert_not_called()

    def test_corrupted_image(self):
        self.assertEqual(self.upload(data=b'not an image').status_code,400)
        self.model.predict.assert_not_called()

    def test_oversized_upload(self):
        from app.utils.image_processing import MAX_IMAGE_BYTES
        self.assertEqual(self.upload(data=b'x'*(MAX_IMAGE_BYTES+1)).status_code,400)
        self.model.predict.assert_not_called()

    def test_no_detections(self):
        self.model.predict.return_value=result([])
        response=self.upload()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['detections'],[])
        self.assertEqual(response.json()['detection_count'],0)
        self.assertTrue(response.json()['success'])

    def test_configurable_threshold(self):
        with patch.dict(os.environ,{'DIET_DETECTION_CONFIDENCE':'.8'}):
            response=self.upload()
        self.assertEqual(response.json()['detection_count'],1)
        self.assertEqual(self.model.predict.call_args.kwargs['conf'],.8)

    def test_invalid_configuration_returns_sanitized_500(self):
        with patch.dict(os.environ,{'DIET_DETECTION_CONFIDENCE':'nan'}):
            response=self.upload()
        self.assertEqual(response.status_code,500)
        self.assertNotIn(str(service.PACKAGE),response.text)

    def test_model_load_failure_returns_500(self):
        self.patcher.stop()
        with patch.object(service,'get_detector',side_effect=service.DietDetectionError('private/path')):
            response=self.upload()
        self.assertEqual(response.status_code,500)
        self.assertNotIn('private/path',response.text)

    def test_inference_failure_returns_500(self):
        self.model.predict.side_effect=RuntimeError('private/path')
        response=self.upload()
        self.assertEqual(response.status_code,500)
        self.assertNotIn('private/path',response.text)

    def test_invalid_prediction_is_rejected(self):
        for row in [[1,2,90,70,1.1,44],[90,2,1,70,.7,44],[1,2,101,70,.7,44],[1,2,90,70,.7,99]]:
            with self.subTest(row=row):
                self.model.predict.return_value=result([row])
                self.assertEqual(self.upload().status_code,500)

    def test_model_info(self):
        response=self.client.get('/api/diet/model-info')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),dict(selected_model='YOLOv8n',dataset_version='training_v3',class_count=46,input_image_size=640,confidence_threshold=.25))


class DietPackageTests(unittest.TestCase):
    def test_real_package_and_singleton_load(self):
        for filename in ['best.pt','class_names.json','model_metadata.json','model_package_integrity.json']:
            self.assertTrue((service.PACKAGE/filename).is_file())
        names={int(k):v for k,v in json.loads((service.PACKAGE/'class_names.json').read_text()).items()}
        self.assertEqual(len(names),46)
        self.assertEqual(set(names),set(range(46)))
        from ultralytics import YOLO
        previous=service._detector
        service._detector=None
        try:
            with patch('ultralytics.YOLO',wraps=YOLO) as loader:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    detectors=list(pool.map(lambda _:service.get_detector(),range(4)))
                self.assertEqual(loader.call_count,1)
                self.assertTrue(all(d is detectors[0] for d in detectors))
                self.assertEqual(detectors[0].class_names,names)
                self.assertEqual(detectors[0].model.names,names)
                # Two API requests reuse the real loaded bundle; predictions remain mocked.
                app=FastAPI();app.include_router(router,prefix='/api')
                with patch.object(detectors[0].model,'predict',return_value=result([])):
                    with TestClient(app) as client:
                        for _ in range(2):
                            self.assertEqual(client.post('/api/diet/detect-food',files={'image':('meal.png',image_bytes(),'image/png')}).status_code,200)
                self.assertEqual(loader.call_count,1)
        finally:
            service._detector=previous

    def test_mapping_mismatch_has_clear_runtime_error(self):
        previous=service._detector
        service._detector=None
        try:
            with patch('ultralytics.YOLO',return_value=SimpleNamespace(task='detect',names={0:'wrong'})):
                with self.assertRaisesRegex(service.DietDetectionError,'class mapping'):
                    service.get_detector()
        finally:
            service._detector=previous

    def test_main_app_health_and_routes(self):
        from app.main import app
        with TestClient(app) as client:
            self.assertEqual(client.get('/health').status_code,200)
            paths=client.get('/openapi.json').json()['paths']
        self.assertIn('post',paths['/api/diet/detect-food'])
        self.assertIn('get',paths['/api/diet/model-info'])


if __name__=='__main__':unittest.main()
