import requests
import re
from .config import GACHA_TABLE_URL, CHAR_TABLE_URL

class GameDataFetcher:
    def __init__(self):
        self.recruit_pool = []

    def fetch_data(self):
        try:
            print("Fetching data from GitHub...")
            gacha_res = requests.get(GACHA_TABLE_URL).json()
            char_res = requests.get(CHAR_TABLE_URL).json()
            self._parse_pool(gacha_res, char_res)
            print(f"Data Loaded: {len(self.recruit_pool)} operators found.")
            
            for rarity in range(1, 7):
                ops = [op['name'] for op in self.recruit_pool if op['rarity'] == rarity]
                print(f"  {rarity}★: {len(ops)} operators")
            
            return self.recruit_pool
        except Exception as e:
            print(f"Error fetching data: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_pool(self, gacha, chars):
        recruit_detail = gacha.get("recruitDetail", "")
        
        clean_detail = re.sub(r"<[^>]*>", "", recruit_detail)
        clean_detail = clean_detail.replace("\\n", "\n")
        
        valid_names = set()
        for part in re.split(r"[/\n\r]+", clean_detail):
            name = part.strip()
            if name and not re.match(r"^[\d★\-\s]*$", name) and len(name) > 1:
                valid_names.add(name.lower())
        
        print(f"  Found {len(valid_names)} valid operator names in recruit pool")

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

            prof_map = {
                "warrior": "guard", 
                "tank": "defender", 
                "pioneer": "vanguard", 
                "special": "specialist",
                "medic": "medic",
                "sniper": "sniper",
                "caster": "caster",
                "supporter": "supporter"
            }
            for k, v in prof_map.items():
                if k in tags:
                    tags.discard(k)
                    tags.add(v)
            
            pos_map = {"melee": "melee", "ranged": "ranged"}
            for k, v in pos_map.items():
                if k in tags:
                    tags.add(v)

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