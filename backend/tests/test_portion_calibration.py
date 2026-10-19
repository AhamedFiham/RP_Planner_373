"""Train-only quantile derivation and calibrated serving-category regression tests."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml
from app.services import portion_estimation_service as service

spec=importlib.util.spec_from_file_location('calibrate_portions',Path('scripts/diet_dataset/calibrate_portion_categories.py'))
calibration=importlib.util.module_from_spec(spec);spec.loader.exec_module(calibration)


def box(name,cid,x1=0,x2=20):
    return dict(class_id=cid,food_name=name,confidence=.9,bounding_box=dict(x1=x1,y1=0,x2=x2,y2=20))


class CalibrationTests(unittest.TestCase):
    def test_linear_percentiles(self):
        values=list(range(1,11))
        self.assertAlmostEqual(calibration.percentile(values,.33),3.97)
        self.assertAlmostEqual(calibration.percentile(values,.67),7.03)

    def test_train_only_support_class_specific_and_dataset_immutable(self):
        reference=service.load_portion_reference()
        names=yaml.safe_load(Path('datasets/diet/training_v3/data.yaml').read_text())['names']
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'data.yaml').write_text(yaml.safe_dump({'nc':46,'names':names}))
            for split in ['train','valid','test']:(root/split/'labels').mkdir(parents=True)
            # Validation/test deliberately contain malformed adversarial annotations.
            for split in ['valid','test']:(root/split/'labels/poison.txt').write_text('NOT A BOX')
            for i in range(10):
                (root/f'train/labels/{i}.txt').write_text(f'44 .5 .5 {(i+1)/100} .2\n15 .5 .5 {(i+1)/100} .1\n')
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            original=Path.read_text
            def guarded(path,*args,**kwargs):
                if path.is_relative_to(root/'valid') or path.is_relative_to(root/'test'):
                    raise AssertionError('Calibration accessed a held-out split')
                return original(path,*args,**kwargs)
            with patch.object(Path,'read_text',guarded):
                config,rows,summary=calibration.calibrate(root,reference)
            self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
            rice=config['foods']['White_Rice'];dhal=config['foods']['Dhal_Curry']
            self.assertAlmostEqual(rice['portion_rules']['small_max_relative_area'],.00794)
            self.assertAlmostEqual(dhal['portion_rules']['small_max_relative_area'],.00397)
            self.assertEqual(rice['training_samples'],10)
            self.assertEqual(config['foods']['Chicken_Curry']['calibration_status'],'insufficient_training_support')
            self.assertIsNone(config['foods']['Chicken_Curry']['portion_rules'])
            self.assertFalse(summary['test_used']);self.assertFalse(summary['validation_used'])
            self.assertTrue(all(name.startswith('train/') or name=='data.yaml' for name in summary['dataset_inputs_sha256']))
            with patch.object(service,'load_portion_reference',return_value=config):
                out=service.estimate_portions([box('Chicken_Curry',9)],100,100)
            self.assertEqual(out.portion_summary[0].portion_category,'Unknown')
            self.assertEqual(out.portion_summary[0].calibration_status,'insufficient_training_support')

    def test_category_boundaries_from_actual_rules(self):
        rule=service.load_portion_reference()['foods']['White_Rice']
        lo=rule['portion_rules']['small_max_relative_area'];hi=rule['portion_rules']['medium_max_relative_area']
        self.assertEqual(service.category(lo,rule),'Small')
        self.assertEqual(service.category((lo+hi)/2,rule),'Medium')
        self.assertEqual(service.category(hi,rule),'Medium')
        self.assertEqual(service.category((hi+1)/2,rule),'Large')

    def test_count_rules_and_no_grams(self):
        for n,expected in [(1,'Small'),(2,'Medium'),(3,'Large'),(4,'Large')]:
            with self.subTest(n=n):
                detections=[box('Cutlet',13,i*25,i*25+20) for i in range(n)]
                out=service.estimate_portions(detections,100,100)
                summary=out.portion_summary[0]
                self.assertEqual(summary.count,n)
                self.assertEqual(summary.portion_category,expected)
                self.assertTrue(all(d.portion.portion_category==expected for d in out.foods))
                self.assertIsNone(summary.estimated_grams)
                self.assertFalse(summary.validated)

    def test_overlap_and_reference_unknown(self):
        out=service.estimate_portions([box('Cutlet',13),box('Cutlet',13,10,30)],100,100)
        self.assertEqual(out.portion_summary[0].portion_category,'Unknown')
        self.assertIsNone(out.portion_summary[0].count)
        out=service.estimate_portions([box('String_Hoppers',40)],100,100)
        self.assertEqual(out.portion_summary[0].portion_category,'Unknown')

    def test_real_train_thresholds_match_config_and_provenance(self):
        dataset=Path('datasets/diet/training_v3')
        config,rows,summary=calibration.calibrate(dataset,service.load_portion_reference())
        self.assertEqual(config,service.load_portion_reference())
        self.assertEqual(summary['area_classes_calibrated'],37)
        self.assertFalse(summary['insufficient_support'])
        self.assertEqual(summary['train_annotations'],4604)


if __name__=='__main__':unittest.main()
