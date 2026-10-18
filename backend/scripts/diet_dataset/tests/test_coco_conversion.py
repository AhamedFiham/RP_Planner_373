import unittest
from diet_dataset.validation import convert_bbox

class CocoTests(unittest.TestCase):
    def test_supplied_bbox_conversion(self):
        self.assertEqual(convert_bbox([10,20,40,20],100,100),[.3,.3,.4,.2])
    def test_reject_missing_or_overflow(self):
        for box in [[],[-1,2,3,4],[90,0,20,10]]:
            with self.assertRaises(ValueError):convert_bbox(box,100,100)
