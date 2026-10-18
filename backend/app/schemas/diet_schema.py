"""Food detection responses; boxes use pixels in the decoded input image."""
from pydantic import BaseModel, Field, model_validator


class BoundingBox(BaseModel):
    x1: float = Field(ge=0, allow_inf_nan=False)
    y1: float = Field(ge=0, allow_inf_nan=False)
    x2: float = Field(gt=0, allow_inf_nan=False)
    y2: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode='after')
    def ordered(self):
        if self.x1 >= self.x2 or self.y1 >= self.y2:
            raise ValueError('Bounding box must have positive width and height')
        return self


class FoodDetection(BaseModel):
    class_id: int = Field(ge=0, le=45)
    food_name: str
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    bounding_box: BoundingBox


class FoodDetectionResponse(BaseModel):
    success: bool = True
    detection_count: int = Field(ge=0)
    detections: list[FoodDetection]
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    model_name: str
    confidence_threshold: float = Field(ge=0, le=1)


class DietModelInfo(BaseModel):
    selected_model: str
    dataset_version: str
    class_count: int
    input_image_size: int
    confidence_threshold: float
