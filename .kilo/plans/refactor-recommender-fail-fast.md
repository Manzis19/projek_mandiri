# Refactor Recommender Fail-Fast Validation

## Goal
Fix the critical image-processing logic vulnerability in `core/recommender.py` by validating the raw image before any preprocessing, resizing, denoising, or detection occurs.

## Root Cause
Current `HairstyleRecommender.analyze()` preprocesses the image before validation:

1. `img_bgr = self.prep.load_image(image_source)`
2. `stages = self.prep.run(img_bgr, debug=True)`
3. `gray = stages["denoised"]`
4. `is_valid, msg = self.detector.validate_photo(gray)`

This is unsafe because:

- resizing can upscale low-resolution images past the minimum resolution threshold;
- CLAHE/Gaussian preprocessing can alter blur characteristics;
- validation no longer measures the original image quality.

## Required Change
Update `core/recommender.py`, specifically `HairstyleRecommender.analyze()` around line 27, to validate the raw image immediately after loading.

The new beginning of `analyze()` must be:

```python
def analyze(self, image_source, top_n=5):
    """
    Pipeline lengkap: foto → rekomendasi hairstyle.

    Return dict:
    {
        "success"      : True/False,
        "error"        : str | None,
        "face_shape"   : "oval" | ...,
        "label"        : "Oval" | ...,
        "confidence"   : 0.85,
        "reasoning"    : "...",
        "scores"       : { "oval": 0.4, ... },
        "features"     : { "wh_ratio": ..., ... },
        "hairstyles"   : [ { name, description, images, tags }, ... ],
        "annotated_img": np.ndarray (BGR),
    }
    """
    try:
        img_bgr = self.prep.load_image(image_source)
        gray_original = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        is_valid, msg = self.detector.validate_photo(gray_original)
        if not is_valid:
            return {"success": False, "error": msg}

        stages = self.prep.run(img_bgr, debug=True)
        gray = stages["denoised"]
        bbox, err = self.detector.detect(gray)
```

Note: the user-provided sequence mentions `cv2.COLOR_BG2GRAY`, but that OpenCV constant is invalid. The correct constant is `cv2.COLOR_BGR2GRAY`.

## Preserve Existing Behavior
After the fail-fast validation passes, keep the existing detection and recommendation logic unchanged:

1. If detection returns an error, return `{"success": False, "error": err["error"]}`.
2. Detect landmarks with `self.landmark.detect(gray, bbox, debug=True)`.
3. Extract features with `self.landmark.extract_features(lm_result["points"])`.
4. Predict shape with `self.classifier.predict(features)`.
5. Retrieve hairstyle recommendations with `self._get_recommendations(shape, top_n)`.
6. Draw the bounding box on the landmark-annotated image.
7. Return the same success dictionary shape as before.
8. Keep the outer `except Exception as e` behavior unchanged:
   ```python
   return {"success": False, "error": f"Terjadi kesalahan: {str(e)}"}
   ```

## Implementation Steps
1. Open `core/recommender.py`.
2. Replace the preprocessing-before-validation block inside `analyze()` with the fail-fast raw-image validation block.
3. Ensure `cv2` is imported; current file does not directly import `cv2`, so add:
   ```python
   import cv2
   ```
   at the top of `core/recommender.py`.
4. Confirm the rest of the method remains unchanged.
5. Run a focused syntax/import check for `core.recommender` if dependencies are available.

## Validation
After implementation, verify:

- `analyze()` now calls `self.detector.validate_photo(gray_original)` before `self.prep.run(...)`.
- Invalid low-resolution or blurry raw images return early without preprocessing.
- Valid images continue through the same pipeline as before.
- No subsequent detection, landmark, classifier, recommendation, or error-handling logic changes.
