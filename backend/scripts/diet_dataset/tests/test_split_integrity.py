import unittest
from pathlib import Path
from diet_dataset.image_groups import assign_splits

class SplitTests(unittest.TestCase):
    def test_deterministic_disjoint_classification(self):
        def rows():return [dict(task='classification',canonical='Apple',path=Path(str(i)),split='unsplit') for i in range(10)]
        first,second=rows(),rows();assign_splits(first);assign_splits(second)
        self.assertEqual(first,second)
        counts={s:sum(r['split']==s for r in first) for s in ['train','valid','test']}
        self.assertEqual(counts,dict(train=7,valid=2,test=1))
        groups=[{r['path'] for r in first if r['split']==s} for s in counts]
        self.assertFalse(groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2])

    def test_existing_classification_split_preserved(self):
        rows=[dict(task='classification',canonical='Apple',path=Path('image'),split='valid',preserve_split=True)]
        assign_splits(rows)
        self.assertEqual(rows[0]['split'],'valid')
