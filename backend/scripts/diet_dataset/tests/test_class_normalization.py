import unittest
from diet_dataset.dataset_sources import decision, category

class ClassTests(unittest.TestCase):
    def test_requested_aliases(self):
        for variants,target in [(['Dhal Curry','dhal','dhal_curry'],'Dhal_Curry'),(['Beat','Beetroot'],'Beetroot'),(['Milk Rice','Kiribath'],'Kiribath'),(['Pitu white','Pittu White'],'White_Pittu')]:
            for value in variants: self.assertEqual(decision(value)[0],target)
    def test_keep_distinctions(self):
        self.assertNotEqual(decision('Unpolished Rice')[0],decision('Red Rice')[0])
        self.assertNotEqual(decision('Kotu Roti')[0],decision('Kottu')[0])
    def test_remove_unknowns_and_invalid(self):
        for name in ['json','spoon','Curb','Del_Curry','Flavourd Mild Cartoons']: self.assertIsNone(decision(name)[0])
        self.assertEqual(category('Dhal_Curry'),'Legumes')
