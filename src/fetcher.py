import requests
import re
import json
import hashlib
from pathlib import Path
from .config import GACHA_TABLE_URL, CHAR_TABLE_URL

CACHE_FILE = Path(__file__).parent.parent / ".operator_cache.json"
CACHE_TTL_HOURS = 24

_RE_HTML_TAGS = re.compile(r"<[^>]*>")
_RE_RARITY_HEADER = re.compile(r"^[\d★\-\s]*$")
_RE_SPLIT = re.compile(r"[/\n\r]+")

PROF_MAP = {
    "warrior": "guard", 
    "tank": "defender", 
    "pioneer": "vanguard", 
    "special": "specialist",
    "support": "supporter",
    "medic": "medic",
    "sniper": "sniper",
    "caster": "caster",
}

class GameDataFetcher:
    __slots__ = ('recruit_pool',)
    
    def __init__(self):
        self.recruit_pool = []

    def fetch_data(self):
        cached = self._load_cache()
        if cached:
            self.recruit_pool = cached
            print(f"Loaded {len(self.recruit_pool)} operators from cache")
            # Debug: check supporter count
            supporter_ops = [op['name'] for op in self.recruit_pool if 'supporter' in op['tags']]
            print(f"  Supporters in pool: {len(supporter_ops)}")
            return self.recruit_pool
        
        try:
            print("Fetching data from GitHub...")
            with requests.Session() as session:
                gacha_res = session.get(GACHA_TABLE_URL, timeout=10).json()
                char_res = session.get(CHAR_TABLE_URL, timeout=10).json()
            
            self._parse_pool(gacha_res, char_res)
            print(f"Data Loaded: {len(self.recruit_pool)} operators found.")
            
            self._save_cache()
            return self.recruit_pool
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []
    
    def _load_cache(self):
        if not CACHE_FILE.exists():
            return None
        
        try:
            import time
            cache_age = time.time() - CACHE_FILE.stat().st_mtime
            if cache_age > CACHE_TTL_HOURS * 3600:
                return None
            
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for op in data:
                    op['tags'] = set(op['tags'])
                return data
        except Exception:
            return None
    
    def _save_cache(self):
        try:
            data = []
            for op in self.recruit_pool:
                data.append({
                    "name": op["name"],
                    "rarity": op["rarity"],
                    "tags": list(op["tags"])
                })
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

    def _parse_pool(self, gacha, chars):
        recruit_detail = gacha.get("recruitDetail", "")
        
        clean_detail = _RE_HTML_TAGS.sub("", recruit_detail)
        clean_detail = clean_detail.replace("\\n", "\n")
        
        valid_names = set()
        for part in _RE_SPLIT.split(clean_detail):
            name = part.strip()
            if name and not _RE_RARITY_HEADER.match(name) and len(name) > 1:
                valid_names.add(name.lower())

        for char_id, data in chars.items():
            name = data.get("name")
            if not name or name.lower() not in valid_names:
                continue
            if data.get("isNotObtainable", False):
                continue

            tags = {t.lower() for t in (data.get("tagList") or [])}
            profession = data.get("profession", "").lower()
            position = data.get("position", "").lower()
            tags.add(profession)
            tags.add(position)

            if profession in PROF_MAP:
                tags.discard(profession)
                tags.add(PROF_MAP[profession])
            
            if position in ("melee", "ranged"):
                tags.add(position)

            rarity = data.get("rarity", 0)
            if isinstance(rarity, str) and rarity.startswith("TIER_"):
                rarity = int(rarity.split("_")[1]) - 1
            
            disp_rarity = int(rarity) + 1

            if disp_rarity == 6: tags.add("top operator")
            if disp_rarity == 5: tags.add("senior operator")
            if disp_rarity == 1: tags.add("robot")
            if disp_rarity == 2: tags.add("starter")

            self.recruit_pool.append({
                "name": name,
                "rarity": disp_rarity,
                "tags": tags
            })