import unittest
from diet_dataset.validation import parse_row

class YoloTests(unittest.TestCase):
    def test_valid_detection_and_existing_polygon(self):
        self.assertEqual(parse_row('1 .5 .5 .4 .2',{1})[1],[.5,.5,.4,.2])
        _,bbox,mode=parse_row('1 .2 .2 .8 .2 .8 .8 .2 .8',{1})
        self.assertAlmostEqual(bbox[2],.6)
        self.assertEqual(mode,'YOLO_polygon_to_bbox')
    def test_invalid_rows(self):
        for line in ['2 .5 .5 .2 .2','1 nan .5 .2 .2','1 .5 .5 0 .2','1 .1 .1 .8 .8','1 .5 .5 1.1 .2','1 .2']:
            with self.assertRaises(ValueError,msg=line): parse_row(line,{1})

class FinalV2VerificationTests(unittest.TestCase):
    def test_strict_detection_row_rejects_extra_columns_and_noninteger_tokens(self):
        from diet_dataset.verify_training_v2 import strict_row
        for line in ['1 .2 .2 .3 .3 .4 .4', '1.0 .5 .5 .2 .2', '46 .5 .5 .2 .2', '1 NaN .5 .2 .2', '']:
            with self.assertRaises(ValueError): strict_row(line)
        self.assertEqual(strict_row('45 .5 .5 .2 .2')[0],45)

    def test_yaml_duplicate_ids_rejected(self):
        import yaml
        from diet_dataset.verify_training_v2 import UniqueLoader
        with self.assertRaises(ValueError):
            yaml.load('names:\n  0: Rice\n  0: Dhal\n', Loader=UniqueLoader)

class ApprovedV3CorrectionTests(unittest.TestCase):
    def test_removes_only_exact_approved_omelette_line(self):
        from diet_dataset.correct_training_v3 import approved_lines,APPROVED,OMELETTE
        old=APPROVED[('train',OMELETTE)]['old']
        valid='0 0.5 0.5 0.2 0.2\n'
        new,rule=approved_lines('train',OMELETTE,old+'\n'+valid)
        self.assertEqual(new,valid)
        self.assertEqual(rule['action'],'removed_invalid_annotation')

    def test_uncertain_kokis_excluded_without_guessing(self):
        from diet_dataset.correct_training_v3 import approved_lines,APPROVED,KOKIS
        line=APPROVED[('train',KOKIS)]['old']+'\n'
        self.assertIsNone(approved_lines('train',KOKIS,line)[0])
        with self.assertRaises(ValueError):approved_lines('train',KOKIS,line+'0 .5 .5 .2 .2\n')

    def test_unapproved_labels_and_geometry_unchanged(self):
        from diet_dataset.correct_training_v3 import approved_lines,OMELETTE
        text='0 0.5000 0.5000 0.2000 0.2000\n'
        self.assertEqual(approved_lines('train','unrelated',text),(text,None))
        with self.assertRaises(ValueError):approved_lines('train',OMELETTE,text)

class BaselineTrainingSetupTests(unittest.TestCase):
    def test_device_detection_cuda_mps_cpu(self):
        from types import SimpleNamespace
        from diet_dataset.train_yolov8n import select_device
        def fake(cuda,mps):
            return SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:cuda),backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda:mps)))
        self.assertEqual(select_device(fake(True,True)),'cuda:0')
        self.assertEqual(select_device(fake(False,True)),'mps')
        self.assertEqual(select_device(fake(False,False)),'cpu')

    def test_generated_caches_never_write_beside_dataset(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from diet_dataset.train_yolov8n import redirect_cache_writer
        with TemporaryDirectory() as tmp:
            root=Path(tmp);original=root/'dataset/train/labels.cache'
            def writer(prefix,path,x,version):
                path.write_text('cache');return path
            redirected=redirect_cache_writer(writer,root/'experiment/cache')
            result=redirected('',original,{},'1')
            self.assertTrue(result.is_file())
            self.assertTrue(result.is_relative_to(root/'experiment/cache'))
            self.assertFalse(original.exists())

class ResumeEpochLimitTests(unittest.TestCase):
    def test_resume_uses_30_total_even_if_checkpoint_restores_100(self):
        from types import SimpleNamespace
        from diet_dataset.train_yolov8n import resume_trainer_for_epochs
        class FakeTrainer:
            def check_resume(self,overrides):
                self.resume=True
                self.args=SimpleNamespace(epochs=100)
        trainer=resume_trainer_for_epochs(FakeTrainer,30)()
        trainer.check_resume({})
        self.assertEqual(trainer.args.epochs,30)
