"""Debug script to check recruitment pool parsing and calculator"""
from src.fetcher import GameDataFetcher
from src.calculator import RecruitCalculator

def main():
    f = GameDataFetcher()
    pool = f.fetch_data()
    calc = RecruitCalculator(pool)
    
    print("\n" + "="*60)
    print("TESTING CALCULATOR")
    print("="*60)
    
    # Test Guard tag
    print("\n--- Testing 'Guard' tag ---")
    results = calc.calculate(['Guard'])
    for r in results:
        if r['tags'] == ['guard']:
            print(f"Guard combo: min={r['min']}★, max={r['max']}★")
            print(f"Operators ({len(r['ops'])}):")
            for op in r['ops'][:10]:  # Show first 10
                print(f"  {op['rarity']}★ {op['name']}")
            if len(r['ops']) > 10:
                print(f"  ... and {len(r['ops']) - 10} more")
    
    # Test Slow tag
    print("\n--- Testing 'Slow' tag ---")
    results = calc.calculate(['Slow'])
    for r in results:
        if r['tags'] == ['slow']:
            print(f"Slow combo: min={r['min']}★, max={r['max']}★")
            print(f"Operators ({len(r['ops'])}):")
            for op in r['ops']:
                print(f"  {op['rarity']}★ {op['name']}")
    
    # Test DPS + Caster
    print("\n--- Testing 'DPS' + 'Caster' tags ---")
    results = calc.calculate(['DPS', 'Caster'])
    for r in results:
        if set(r['tags']) == {'dps', 'caster'}:
            print(f"DPS+Caster combo: min={r['min']}★, max={r['max']}★")
            print(f"Operators ({len(r['ops'])}):")
            for op in r['ops']:
                print(f"  {op['rarity']}★ {op['name']}")
    
    # Check what tags Steward has
    print("\n--- Checking Steward (3★ Caster) tags ---")
    for op in pool:
        if op['name'] == 'Steward':
            print(f"Steward tags: {op['tags']}")
            print(f"Has 'dps': {'dps' in op['tags']}")
            print(f"Has 'caster': {'caster' in op['tags']}")

if __name__ == "__main__":
    main()
