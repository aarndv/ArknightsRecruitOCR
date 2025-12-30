import cv2
import numpy as np
import easyocr
from PIL import ImageGrab
from fuzzywuzzy import process
from datetime import datetime
from .config import VALID_TAGS

class ScreenScanner:
    def __init__(self):
        self.log_file = "ocr_debug.log"
        # Initialize EasyOCR reader (English only, GPU if available)
        self._log("Initializing EasyOCR...")
        
        # Check if CUDA/GPU is available
        gpu_available = self._check_gpu()
        
        self.reader = easyocr.Reader(['en'], gpu=gpu_available)
        self._log(f"EasyOCR initialized (GPU={gpu_available}).")
    
    def _check_gpu(self):
        """Check GPU availability with detailed diagnostics"""
        try:
            import torch
            self._log(f"PyTorch version: {torch.__version__}")
            
            # Check CUDA compilation
            cuda_compiled = torch.version.cuda is not None
            self._log(f"PyTorch compiled with CUDA: {cuda_compiled}")
            if cuda_compiled:
                self._log(f"  CUDA version in PyTorch: {torch.version.cuda}")
            
            # Check cuDNN
            if hasattr(torch.backends, 'cudnn'):
                self._log(f"cuDNN available: {torch.backends.cudnn.is_available()}")
                if torch.backends.cudnn.is_available():
                    self._log(f"  cuDNN version: {torch.backends.cudnn.version()}")
            
            # Check CUDA availability
            cuda_available = torch.cuda.is_available()
            self._log(f"CUDA runtime available: {cuda_available}")
            
            if cuda_available:
                device_count = torch.cuda.device_count()
                self._log(f"GPU count: {device_count}")
                for i in range(device_count):
                    self._log(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
                    props = torch.cuda.get_device_properties(i)
                    self._log(f"    Memory: {props.total_memory / 1024**3:.1f} GB")
                    self._log(f"    Compute capability: {props.major}.{props.minor}")
                return True
            else:
                self._log("")
                self._log("⚠ CUDA not available. Diagnostic info:")
                if not cuda_compiled:
                    self._log("  → PyTorch was installed WITHOUT CUDA support")
                    self._log("  → Fix: pip uninstall torch && pip install torch --index-url https://download.pytorch.org/whl/cu118")
                else:
                    self._log("  → PyTorch has CUDA but runtime check failed")
                    self._log("  → Possible causes:")
                    self._log("    - NVIDIA driver not installed or outdated")
                    self._log("    - No NVIDIA GPU in this system")
                    self._log("    - CUDA toolkit version mismatch")
                self._log("")
                return False
                
        except ImportError as e:
            self._log(f"PyTorch not found: {e}")
            self._log("EasyOCR will use CPU mode.")
            return False
        except Exception as e:
            self._log(f"Error checking GPU: {e}")
            import traceback
            self._log(traceback.format_exc())
            return False
    
    def _log(self, message, also_print=True):
        """Write to log file and optionally print to console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
        if also_print:
            print(message)
    
    def capture_screen(self):
        screen = ImageGrab.grab()
        return cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

    def scan_for_tags(self, img):
        # Start new scan entry in log
        self._log("\n" + "="*50)
        self._log("NEW SCAN STARTED")
        self._log("="*50)
        
        # --- 1. CROP ---
        h, w, _ = img.shape
        self._log(f"Screen size: {w}x{h}")
        
        # Crop to the tag area (Job Tags section)
        y1, y2 = int(h * 0.50), int(h * 0.72)
        x1, x2 = int(w * 0.30), int(w * 0.68)
        roi = img[y1:y2, x1:x2]
        self._log(f"ROI crop: x={x1}-{x2}, y={y1}-{y2}")

        # Store crop offsets for coordinate conversion
        self.crop_offset = (x1, y1)
        self.scale = 2

        # --- 2. PREPROCESSING ---
        # Scale up 2x for better OCR accuracy
        roi_resized = cv2.resize(roi, (0, 0), fx=self.scale, fy=self.scale, interpolation=cv2.INTER_LINEAR)
        self._log(f"Scaled ROI size: {roi_resized.shape[1]}x{roi_resized.shape[0]} (scale={self.scale}x)")

        # Save the ROI for debugging
        cv2.imwrite("debug_roi.png", roi_resized)

        # --- 3. RUN OCR with EasyOCR ---
        self._log("Running EasyOCR...")
        results = self.reader.readtext(roi_resized)
        
        self._log(f"\n--- EASYOCR RAW OUTPUT ({len(results)} detections) ---")
        found_tags = {}  # Changed to dict: tag_name -> screen_bbox
        
        for (bbox, text, confidence) in results:
            text = text.strip()
            self._log(f"  Detected: '{text}' (confidence: {confidence:.2f})")
            
            # Skip low confidence or very short text
            if confidence < 0.3:
                self._log(f"    ✗ Skipped (confidence < 0.3)")
                continue
            if len(text) < 2:
                self._log(f"    ✗ Skipped (too short)")
                continue
                
            # Fuzzy match against valid tags
            match, score = process.extractOne(text, VALID_TAGS)
            self._log(f"    -> Best match: '{match}' (score: {score})")
            
            # Require high score for a match
            if score >= 75:
                # Convert bbox to screen coordinates
                screen_bbox = self._bbox_to_screen(bbox)
                found_tags[match] = screen_bbox
                self._log(f"    ✓ ACCEPTED (screen pos: {screen_bbox})")
            else:
                self._log(f"    ✗ Rejected (score < 75)")

        # Save a debug image with bounding boxes
        debug_img = roi_resized.copy()
        for (bbox, text, confidence) in results:
            if confidence >= 0.3:
                pts = np.array(bbox, dtype=np.int32)
                cv2.polylines(debug_img, [pts], True, (0, 255, 0), 2)
                cv2.putText(debug_img, text, (pts[0][0], pts[0][1] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imwrite("debug_view.png", debug_img)
        self._log(f"\n--- RESULT ---")
        self._log(f"Found tags: {list(found_tags.keys())}")
        self._log("="*50 + "\n")

        return found_tags, debug_img
    
    def _bbox_to_screen(self, bbox):
        """Convert OCR bbox (scaled ROI coords) to actual screen coordinates"""
        # bbox is list of 4 points: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        # Convert from scaled ROI to original screen coords
        x_offset, y_offset = self.crop_offset
        
        # Get bounding rectangle
        pts = np.array(bbox)
        x_min = int(pts[:, 0].min() / self.scale + x_offset)
        x_max = int(pts[:, 0].max() / self.scale + x_offset)
        y_min = int(pts[:, 1].min() / self.scale + y_offset)
        y_max = int(pts[:, 1].max() / self.scale + y_offset)
        
        return (x_min, y_min, x_max, y_max)