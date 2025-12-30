import os

GACHA_TABLE_URL = "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/en/gamedata/excel/gacha_table.json"
CHAR_TABLE_URL = "https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/en/gamedata/excel/character_table.json"

TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

VALID_TAGS = [
    "Guard", "Sniper", "Defender", "Medic", "Supporter", "Caster", "Specialist", "Vanguard",
    "Melee", "Ranged", "Top Operator", "Senior Operator", "Starter", "Robot",
    "Healing", "Support", "DPS", "AoE", "Slow", "Survival", "Tank", "Defense",
    "DP-Recovery", "Fast-Redeploy", "Shift", "Summon", "Crowd-Control", "Nuker", "Debuff"
]