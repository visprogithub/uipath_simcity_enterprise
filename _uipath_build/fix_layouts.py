"""Spread building positions across 4 quadrants in all scenario files (fixes the y:1 pile-up)."""
import re
import pathlib

# 7 positions: 2 top-left, 2 top-right, 2 bottom-left, 1 bottom-right (roads at y9-10 / x15-16)
LAYOUT = [(2, 2), (9, 2), (19, 2), (26, 2), (2, 12), (9, 12), (19, 12)]
base = pathlib.Path("e:/Repos/uipath_simcity_enterprise/apps/backend/scenarios")

for fn in ["financial_services.py", "retail_ecommerce.py", "manufacturing.py"]:
    p = base / fn
    text = p.read_text(encoding="utf-8")
    n = len(re.findall(r'"pos":\s*\{[^}]*\}', text))
    idx = [0]

    def repl(m):
        i = idx[0]
        idx[0] += 1
        if i < len(LAYOUT):
            x, y = LAYOUT[i]
            return f'"pos": {{"x": {x}, "y": {y}, "w": 4, "h": 4}}'
        return m.group(0)

    new = re.sub(r'"pos":\s*\{[^}]*\}', repl, text)
    p.write_text(new, encoding="utf-8")
    print(f"{fn}: found {n} buildings, repositioned {min(n, len(LAYOUT))}")
