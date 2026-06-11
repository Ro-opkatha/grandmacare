"""
backend/preprocess.py — clean up prescription photos before OCR.

Phone photos of prescriptions routinely have a hand/phone shadow across the
page (this killed two medicines in real testing). Pipeline: estimate the
illumination per channel and divide it out (shadow removal), CLAHE on the
lightness channel (faint ink), then 2x upscale (small handwriting).

Any failure falls back to the original image — preprocessing must never be
the reason an analysis fails.
"""

import os
import tempfile

import cv2
import numpy as np


def _remove_shadows(image):
    planes = []
    for plane in cv2.split(image):
        background = cv2.medianBlur(cv2.dilate(plane, np.ones((7, 7), np.uint8)), 21)
        planes.append(cv2.divide(plane, background, scale=255))
    return cv2.merge(planes)


def _boost_contrast(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab = cv2.merge((clahe.apply(lightness), a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def preprocess_prescription(image_path):
    """Returns a path to the cleaned image (or the original path on failure)."""
    try:
        image = cv2.imread(str(image_path))
        if image is None:
            return image_path

        image = _remove_shadows(image)
        image = _boost_contrast(image)
        image = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

        stem = os.path.splitext(os.path.basename(str(image_path)))[0]
        out_path = os.path.join(tempfile.gettempdir(), f"{stem}_prep.png")
        if not cv2.imwrite(out_path, image):
            return image_path
        return out_path
    except Exception:
        return image_path
