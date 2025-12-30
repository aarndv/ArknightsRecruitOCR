import json
import os
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent / "settings.json"

DEFAULT_SETTINGS = {
    "hotkeys": {
        "scan": "F9",
        "clear": "F10",
        "quick": "F8"
    },
    "overlay": {
        "opacity": 0.90,
        "position_x": 50,
        "position_y": 50
    },
    "features": {
        "auto_click": False,
        "min_rarity": 3
    }
}

HOTKEY_OPTIONS = [
    "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    "Mouse4", "Mouse5",
    "Home", "End", "Insert", "Delete", "PageUp", "PageDown",
    "Ctrl+Shift+S", "Ctrl+Shift+C", "Alt+S", "Alt+C",
    "Num0", "Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7", "Num8", "Num9",
]

class SettingsManager:
    def __init__(self):
        self.settings = self._load_settings()
    
    def _load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded = json.load(f)
                    merged = DEFAULT_SETTINGS.copy()
                    for key, value in loaded.items():
                        if isinstance(value, dict) and key in merged:
                            merged[key].update(value)
                        else:
                            merged[key] = value
                    return merged
            except Exception as e:
                print(f"Error loading settings: {e}")
                return DEFAULT_SETTINGS.copy()
        return DEFAULT_SETTINGS.copy()
    
    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get(self, *keys):
        value = self.settings
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value
    
    def set(self, value, *keys):
        """Set a nested setting value"""
        target = self.settings
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        target[keys[-1]] = value
        self.save_settings()
    
    @property
    def scan_hotkey(self):
        return self.get("hotkeys", "scan")
    
    @scan_hotkey.setter
    def scan_hotkey(self, value):
        self.set(value, "hotkeys", "scan")
    
    @property
    def clear_hotkey(self):
        return self.get("hotkeys", "clear")
    
    @clear_hotkey.setter
    def clear_hotkey(self, value):
        self.set(value, "hotkeys", "clear")
    
    @property
    def quick_hotkey(self):
        return self.get("hotkeys", "quick") or "F8"
    
    @quick_hotkey.setter
    def quick_hotkey(self, value):
        self.set(value, "hotkeys", "quick")
