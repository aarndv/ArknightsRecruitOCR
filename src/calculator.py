import itertools

class RecruitCalculator:
    def __init__(self, pool):
        self.pool = pool

    def calculate(self, selected_tags, sort_mode="min"):
        """
        selected_tags: List of strings (e.g. ['Guard', 'DPS'])
        sort_mode: 'min' (Safe guarantee) or 'max' (Potential high-roll)
        """
        selected_tags = [t.lower() for t in selected_tags]
        results = []

        for r in range(1, 4):
            for combo in itertools.combinations(selected_tags, r):
                combo_set = set(combo)
                matches = []

                for op in self.pool:
                    if combo_set.issubset(op['tags']):
                        if op['rarity'] == 6 and "top operator" not in combo_set:
                            continue
                        
                        if op['rarity'] == 1 and "robot" not in combo_set:
                            continue
                        
                        if op['rarity'] <= 2 and "robot" not in combo_set and "starter" not in combo_set:
                            continue
                            
                        matches.append(op)

                if not matches:
                    continue

                min_rarity = min(op['rarity'] for op in matches)
                max_rarity = max(op['rarity'] for op in matches)
                
                results.append({
                    "tags": list(combo),
                    "min": min_rarity,
                    "max": max_rarity,
                    "ops": sorted(matches, key=lambda x: x['rarity'], reverse=True)
                })

        if sort_mode == "max":
            # Prioritize seeing 6* potentials, then guaranteed 5*
            results.sort(key=lambda x: (x['max'], x['min'], -len(x['ops'])), reverse=True)
        else:
            # Default: Prioritize Guaranteed Rarity (Safety)
            results.sort(key=lambda x: (x['min'], x['max'], -len(x['ops'])), reverse=True)

        return results