import cv2
import numpy as np
from PIL import ImageGrab
from .config import VALID_TAGS

# Build lookup sets for fast exact matching
_VALID_TAGS_LOWER = {t.lower(): t for t in VALID_TAGS}
_SHORT_TAGS = {t.lower(): t for t in VALID_TAGS if len(t) <= 4}  # AoE, DPS, Tank, Slow

# Try rapidfuzz first (faster), fall back to fuzzywuzzy
try:
    from rapidfuzz import process, fuzz
    def fuzzy_match(text, choices, score_cutoff=70):
        text_lower = text.lower()
        # Exact match first (handles short tags like AoE, DPS)
        if text_lower in _VALID_TAGS_LOWER:
            return _VALID_TAGS_LOWER[text_lower], 100
        # Fuzzy match for longer text
        result = process.extractOne(text_lower, choices, scorer=fuzz.ratio, score_cutoff=score_cutoff)
        if result:
            return result[0], result[1]
        return None, 0
except ImportError:
    from fuzzywuzzy import process as fuzz_process
    def fuzzy_match(text, choices, score_cutoff=70):
        text_lower = text.lower()
        # Exact match first
        if text_lower in _VALID_TAGS_LOWER:
            return _VALID_TAGS_LOWER[text_lower], 100
        # Fuzzy match
        result = fuzz_process.extractOne(text, choices)
        if result and result[1] >= score_cutoff:
            return result[0], result[1]
        return None, 0

class ScreenScanner:
    __slots__ = ('reader', 'crop_offset', 'scale', '_gpu_available', '_initialized')
    
    def __init__(self):
        self.reader = None
        self._initialized = False
        self._gpu_available = None
        self.crop_offset = (0, 0)
        self.scale = 2
    
    def _ensure_initialized(self):
        if self._initialized:
            return
        
        import easyocr
        print("Initializing EasyOCR...")
        
        self._gpu_available = self._check_gpu()
        self.reader = easyocr.Reader(['en'], gpu=self._gpu_available, verbose=False)
        self._initialized = True
        print(f"EasyOCR ready (GPU={self._gpu_available})")
    
    def _check_gpu(self):
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
        except Exception:
            return False
    
    def capture_screen(self):
        screen = ImageGrab.grab()
        return cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

    def scan_for_tags(self, img):
        self._ensure_initialized()
        
        h, w, _ = img.shape
        
        # Wide crop to capture all 5 tags (2 rows x 3 columns)
        y1, y2 = int(h * 0.45), int(h * 0.78)
        x1, x2 = int(w * 0.15), int(w * 0.85)
        roi = img[y1:y2, x1:x2]

        self.crop_offset = (x1, y1)

        roi_resized = cv2.resize(roi, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_LINEAR)
        
        # Save debug image
        cv2.imwrite("debug_roi.png", roi_resized)

        results = self.reader.readtext(roi_resized)
        
        found_tags = {}
        
        print(f"OCR detected {len(results)} text regions:")
        for bbox, text, confidence in results:
            text_clean = text.strip()
            print(f"  '{text_clean}' (conf: {confidence:.2f})")
            
            if confidence < 0.25 or len(text_clean) < 2:
                print(f"    -> Skipped (low conf or too short)")
                continue
            
            match, score = fuzzy_match(text_clean, VALID_TAGS, score_cutoff=70)
            
            if match:
                screen_bbox = self._bbox_to_screen(bbox)
                found_tags[match] = screen_bbox
                print(f"    -> Matched: '{match}' (score: {score})")
            else:
                print(f"    -> No match")
        
        print(f"Final tags: {list(found_tags.keys())}")
        return found_tags, None
    
    def _bbox_to_screen(self, bbox):
        x_offset, y_offset = self.crop_offset
        pts = np.array(bbox)
        x_min = int(pts[:, 0].min() / self.scale + x_offset)
        x_max = int(pts[:, 0].max() / self.scale + x_offset)
        y_min = int(pts[:, 1].min() / self.scale + y_offset)
        y_max = int(pts[:, 1].max() / self.scale + y_offset)
        
        return (x_min, y_min, x_max, y_max)