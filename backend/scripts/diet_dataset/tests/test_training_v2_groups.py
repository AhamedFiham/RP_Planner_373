import unittest
from diet_dataset.image_groups import UnionFind, filename_family
from diet_dataset.image_groups import balance
from diet_dataset.build_diet_training_v2 import individually_feasible,status

class TrainingV2Tests(unittest.TestCase):
    def test_roboflow_filename_family(self):
        self.assertEqual(filename_family('image.jpg'),filename_family('image_jpg.rf.abc123.jpg'))
        self.assertEqual(filename_family('meal-42-_jpg.rf.aaa.jpg'),filename_family('meal-42-_jpg.rf.bbb.jpg'))
        self.assertNotEqual(filename_family('meal-42.jpg'),filename_family('meal-43.jpg'))
    def test_transitive_family_duplicate_bridge(self):
        uf=UnionFind();uf.union('retained_a','excluded_b','same_roboflow_original');uf.union('excluded_b','retained_c','near_duplicate')
        self.assertEqual(uf.find('retained_a'),uf.find('retained_c'))
        self.assertEqual(uf.reasons[uf.find('retained_a')],{'same_roboflow_original','near_duplicate'})
    def test_deterministic_balancing_training_floor_and_whole_groups(self):
        groups=[dict(id=str(i),size=10,counts=[10]) for i in range(6)]
        a,info=balance(groups,seed=42,restarts=2)
        b,_=balance(groups,seed=42,restarts=2)
        self.assertEqual(a,b)
        self.assertEqual(len(a),6)
        self.assertGreaterEqual(info['counts'][0][0],15)
        self.assertGreater(info['counts'][0][0],info['counts'][1][0]+info['counts'][2][0])
        self.assertGreaterEqual(info['counts'][1][0],3)
        self.assertGreaterEqual(info['counts'][2][0],3)
    def test_report_true_group_impossibility(self):
        self.assertFalse(individually_feasible([11,11,2],24))
        self.assertFalse(individually_feasible([11,11,11,2],35))
        self.assertTrue(individually_feasible([11,11,11,11,2],46))
        self.assertFalse(individually_feasible([15,2,3],20))
    def test_coverage_status_boundaries(self):
        self.assertEqual([status(n) for n in [0,1,2,3,4,5]],['MISSING','CRITICAL','CRITICAL','LIMITED','LIMITED','GOOD'])
