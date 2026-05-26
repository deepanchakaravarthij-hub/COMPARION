# mypy: ignore-errors
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class PreprocessingOptions:
    denoise: bool = True
    threshold: bool = True
    enhance_contrast: bool = True
    correct_orientation: bool = True
    deskew: bool = True


@dataclass(frozen=True)
class PreprocessingMetadata:
    rotation_degrees: int
    skew_degrees: float
    denoise: bool
    threshold: bool
    enhance_contrast: bool


@dataclass(frozen=True)
class PreprocessedImage:
    image: Image.Image
    metadata: PreprocessingMetadata


def preprocess_image(
    image: Image.Image,
    options: PreprocessingOptions | None = None,
) -> PreprocessedImage:
    options = options or PreprocessingOptions()
    grayscale = np.array(image.convert("L"))
    rotation_degrees = detect_orientation(grayscale) if options.correct_orientation else 0
    rotated = rotate_array(grayscale, rotation_degrees)

    processed = rotated
    if options.enhance_contrast:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        processed = clahe.apply(processed)
    if options.denoise:
        processed = cv2.medianBlur(processed, 3)
    if options.threshold:
        processed = cv2.adaptiveThreshold(
            processed,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

    skew_degrees = estimate_skew(processed) if options.deskew else 0.0
    deskewed = deskew_array(processed, skew_degrees)

    return PreprocessedImage(
        image=Image.fromarray(deskewed).convert("L"),
        metadata=PreprocessingMetadata(
            rotation_degrees=rotation_degrees,
            skew_degrees=round(skew_degrees, 3),
            denoise=options.denoise,
            threshold=options.threshold,
            enhance_contrast=options.enhance_contrast,
        ),
    )


def detect_orientation(gray: np.ndarray) -> int:
    height, width = gray.shape[:2]
    if width > height * 1.15:
        return 270
    return 0


def rotate_array(gray: np.ndarray, degrees: int) -> np.ndarray:
    if degrees == 90:
        return cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
    if degrees == 180:
        return cv2.rotate(gray, cv2.ROTATE_180)
    if degrees == 270:
        return cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return gray


def estimate_skew(gray: np.ndarray) -> float:
    inverted = cv2.bitwise_not(gray)
    coords = cv2.findNonZero(inverted)
    if coords is None or len(coords) < 20:
        return 0.0
    angle = float(cv2.minAreaRect(coords)[-1])
    if angle < -45:
        angle = 90 + angle
    if angle > 45:
        angle = angle - 90
    if abs(angle) < 0.2:
        return 0.0
    return angle


def deskew_array(gray: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.2:
        return gray
    height, width = gray.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        gray,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
