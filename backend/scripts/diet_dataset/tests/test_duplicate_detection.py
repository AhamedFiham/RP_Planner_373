import unittest
from pathlib import Path
from diet_dataset.image_groups import deduplicate

def record(path,split,pixel,dhash):
    return dict(path=Path(path),split=split,dataset='test',pixel_hash=pixel,sha256=pixel,dhash=dhash,width=100,height=100,task='detection')

class DuplicateTests(unittest.TestCase):
    def test_exact_duplicates_keep_test(self):
        kept,duplicates,leakage=deduplicate([record('a','train','same',0),record('b','test','same',0)])
        self.assertEqual(len(kept),1);self.assertEqual(kept[0]['split'],'test')
        self.assertEqual(duplicates[0]['action'],'exclude_exact_duplicate');self.assertEqual(len(leakage),1)
    def test_near_cross_split_quarantined(self):
        kept,duplicates,leakage=deduplicate([record('a','test','one',0),record('b','train','two',1)])
        self.assertEqual(len(kept),1);self.assertEqual(leakage[0]['reason'],'perceptual_candidate')
