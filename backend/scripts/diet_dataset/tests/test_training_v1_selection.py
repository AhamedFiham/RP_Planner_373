import unittest
from diet_dataset.build_diet_training_v1 import select_classes

class TrainingV1Tests(unittest.TestCase):
    def test_selection_boundary_exclusions_and_sequential_ids(self):
        config={};distribution=[]
        for name,total,valid,test,status,classification in [
            ('White_Rice',20,1,1,'available',0),
            ('Dhal_Curry',100,10,5,'available',0),
            ('Carrot',19,1,1,'available',0),
            ('Apple',0,0,0,'available',5),
            ('Red_Rice',0,0,0,'data_needed',0),
            ('Spoon',100,10,5,'available',0),
            ('Curb',50,5,5,'available',0),
            ('Fish',50,5,5,'available',0),
            ('Set_Yoghurt',66,0,0,'available',0),
        ]:
            config[name]=dict(status=status,detection_annotations=total,classification_images=classification,category='Other')
            distribution.append(dict(food_name=name,total_annotations=str(total),train_annotations=str(total-valid-test),valid_annotations=str(valid),test_annotations=str(test),source_datasets='fixture'))
        selected,excluded=select_classes(config,distribution,[])
        self.assertEqual([r['canonical_class_name'] for r in selected],['Dhal_Curry','White_Rice'])
        self.assertEqual([r['new_class_id'] for r in selected],[0,1])
        self.assertEqual(len(excluded),7)
    def test_inconsistent_report_rejected(self):
        with self.assertRaises(ValueError):
            select_classes({'Rice':dict(detection_annotations=20)},[dict(food_name='Rice',total_annotations='19')],[])
