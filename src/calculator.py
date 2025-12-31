from itertools import combinations

class RecruitCalculator:
    __slots__ = ('pool', '_tag_index', '_has_top_op', '_has_robot', '_has_starter')
    
    def __init__(self, pool):
        self.pool = pool
        self._build_tag_index()
    
    def _build_tag_index(self):
        self._tag_index = {}
        self._has_top_op = set()
        self._has_robot = set()
        self._has_starter = set()
        
        for i, op in enumerate(self.pool):
            for tag in op['tags']:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                self._tag_index[tag].append(i)
            
            if "top operator" in op['tags']:
                self._has_top_op.add(i)
            if "robot" in op['tags']:
                self._has_robot.add(i)
            if "starter" in op['tags']:
                self._has_starter.add(i)

    def calculate(self, selected_tags, sort_mode="min"):
        selected_tags = [t.lower() for t in selected_tags]
        results = []
        
        for r in range(1, 4):
            for combo in combinations(selected_tags, r):
                combo_set = frozenset(combo)
                
                if not combo:
                    continue
                
                first_tag = combo[0]
                if first_tag not in self._tag_index:
                    continue
                
                candidate_indices = set(self._tag_index[first_tag])
                for tag in combo[1:]:
                    if tag not in self._tag_index:
                        candidate_indices = set()
                        break
                    candidate_indices &= set(self._tag_index[tag])
                
                if not candidate_indices:
                    continue
                
                has_top_op = "top operator" in combo_set
                has_robot = "robot" in combo_set
                has_starter = "starter" in combo_set
                
                matches = []
                min_rarity = 7
                max_rarity = 0
                
                for idx in candidate_indices:
                    op = self.pool[idx]
                    rarity = op['rarity']
                    
                    if rarity == 6 and not has_top_op:
                        continue
                    if rarity == 1 and not has_robot:
                        continue
                    if rarity <= 2 and not has_robot and not has_starter:
                        continue
                    
                    matches.append(op)
                    if rarity < min_rarity:
                        min_rarity = rarity
                    if rarity > max_rarity:
                        max_rarity = rarity

                if not matches:
                    continue
                
                results.append({
                    "tags": list(combo),
                    "min": min_rarity,
                    "max": max_rarity,
                    "ops": sorted(matches, key=lambda x: x['rarity'], reverse=True)
                })

        if sort_mode == "max":
            results.sort(key=lambda x: (x['max'], x['min'], -len(x['ops'])), reverse=True)
        else:
            results.sort(key=lambda x: (x['min'], x['max'], -len(x['ops'])), reverse=True)

        return results