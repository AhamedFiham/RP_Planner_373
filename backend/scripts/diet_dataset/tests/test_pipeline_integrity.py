import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import hashlib
import json
from unittest.mock import patch
from PIL import Image
from diet_dataset import prepare_diet_dataset as pipeline
from diet_dataset.outputs import write_outputs

class PipelineTests(unittest.TestCase):
    def test_raw_immutable_dry_run_execute_idempotency(self):
        with TemporaryDirectory() as tmp:
            backend=Path(tmp);raw=backend/'datasets/diet/raw';root=raw/'my dataset'
            folder=root/'train/images';folder.mkdir(parents=True);labels=root/'train/labels';labels.mkdir()
            Image.new('RGB',(20,20),'red').save(folder/'meal.jpg')
            (labels/'meal.txt').write_text('0 .5 .5 .4 .4\n1 .5 .5 .2 .2\n')
            (root/'data.yaml').write_text('nc: 2\nnames: [Dhal Curry, spoon]\n')
            (backend/'config').mkdir();reports=backend/'datasets/diet/processed/reports/dry_run'
            before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.rglob('*') if p.is_file()}
            with patch.object(pipeline,'BACKEND',backend):
                data=pipeline.audit(raw);summary,names=pipeline.report(data,reports)
            self.assertFalse((backend/'datasets/diet/normalized').exists())
            self.assertNotIn('Spoon',names)
            write_outputs(data,reports,names,backend,False)
            out=backend/'datasets/diet/normalized/detection/train/labels'
            text=next(out.glob('*.txt')).read_text();self.assertEqual(len(text.splitlines()),1)
            self.assertEqual(text.split()[0],str(names.index('Dhal_Curry')))
            metadata=backend/'datasets/diet/normalized/reports/pipeline_metadata.json';mtime=metadata.stat().st_mtime_ns
            write_outputs(data,reports,names,backend,False);self.assertEqual(metadata.stat().st_mtime_ns,mtime)
            after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
