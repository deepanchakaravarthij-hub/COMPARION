# Edge Cases

- Rotation (90/180/270): orientation detect + rotate.
- Skew: Hough/line-based deskew.
- Scan noise: denoise + adaptive threshold.
- Perspective distortion: homography correction.
- OCR errors: confidence filtering + cleanup.
- Embedded image changes: segment region then specialized compare.
- Watermarks/stamps: optional masking rules.
