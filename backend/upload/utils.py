# backend/upload/utils.py

import os
import cv2
import numpy as np
from PIL import Image
import torch

from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel  # allowlist this class
from config import Config

# Register DetectionModel so torch.load can unpickle the Ultralytics checkpoint
torch.serialization.add_safe_globals([DetectionModel])

_model: YOLO | None = None

def get_model() -> YOLO:
    """Lazily load the YOLO model with safe globals already registered."""
    global _model
    if _model is None:
        # this will now succeed under PyTorch 2.6+'s safe loader
        _model = YOLO('yolov8n.pt')
    return _model

def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def detect_objects(image: Image.Image) -> list[str]:
    """
    Run YOLO inference on a PIL image and return the list of class names detected.
    """
    # convert PIL → OpenCV format
    open_cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # get or load the model
    model = get_model()
    results = model.predict(source=open_cv_image, conf=0.5)

    # collect names
    object_names: list[str] = []
    for result in results:
        object_names.extend([model.names[int(cls)] for cls in result.boxes.cls])

    return object_names
