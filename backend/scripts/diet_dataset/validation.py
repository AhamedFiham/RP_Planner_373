"""Image checks and YOLO/COCO annotation validation."""
from pathlib import Path
import hashlib
from PIL import Image
import math


# Validate images

EXTENSIONS = {'.jpg','.jpeg','.png','.webp'}

def inspect_image(path: Path) -> dict:
    if path.stat().st_size == 0: raise ValueError('zero-byte image')
    with Image.open(path) as image: image.verify()
    with Image.open(path) as image:
        image.load()
        if min(image.size) <= 0: raise ValueError('invalid dimensions')
        if image.getexif().get(274,1) != 1: raise ValueError('EXIF orientation requires annotation-aware review')
        rgb = image.convert('RGB')
        small = rgb.convert('L').resize((9,8))
        pixels = list(small.get_flattened_data()) if hasattr(small, 'get_flattened_data') else list(small.getdata())
        bits = 0
        for y in range(8):
            for x in range(8): bits = (bits << 1) | (pixels[y*9+x] > pixels[y*9+x+1])
        return dict(width=image.width,height=image.height,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pixel_hash=hashlib.sha256(str(image.size).encode()+rgb.tobytes()).hexdigest(),dhash=bits)


# Validate yolo labels

def validate_box(box: list[float]) -> bool:
    if len(box)!=4 or not all(math.isfinite(v) for v in box): return False
    x,y,w,h = box
    return 0<=x<=1 and 0<=y<=1 and 0<w<=1 and 0<h<=1 and x-w/2>=-1e-6 and y-h/2>=-1e-6 and x+w/2<=1+1e-6 and y+h/2<=1+1e-6

def parse_row(line: str, class_ids: set[int]) -> tuple[int,list[float],str]:
    values = [float(v) for v in line.split()]
    if not values or not all(math.isfinite(v) for v in values): raise ValueError('malformed or nonfinite row')
    if not values[0].is_integer() or int(values[0]) not in class_ids: raise ValueError('invalid class ID')
    coords = values[1:]
    mode = 'YOLO_detection'
    if len(coords)>=6 and len(coords)%2==0:
        if not all(0<=v<=1 for v in coords): raise ValueError('polygon coordinates outside [0,1]')
        xs,ys = coords[::2],coords[1::2]
        area = abs(sum(xs[i]*ys[(i+1)%len(xs)]-xs[(i+1)%len(xs)]*ys[i] for i in range(len(xs))))/2
        if area<=0: raise ValueError('zero-area polygon')
        coords = [(min(xs)+max(xs))/2,(min(ys)+max(ys))/2,max(xs)-min(xs),max(ys)-min(ys)]
        mode = 'YOLO_polygon_to_bbox'
    if not validate_box(coords): raise ValueError('invalid bounding box or image-boundary overflow')
    return int(values[0]),coords,mode


# Convert coco to yolo

def convert_bbox(bbox: list[float], width: int, height: int) -> list[float]:
    if len(bbox)!=4 or width<=0 or height<=0: raise ValueError('invalid COCO bbox or dimensions')
    x,y,w,h = bbox
    box = [(x+w/2)/width,(y+h/2)/height,w/width,h/height]
    if not validate_box(box): raise ValueError('invalid or out-of-bounds COCO bbox')
    return box
