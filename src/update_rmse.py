"""
Updates app/main.py with recomputed town RMSE values from the v2 model.
Run from project root: python3 src/update_rmse.py
"""

import re

APP_PATH = "app/main.py"

# ── New values from train_v2.py output ───────────────────────────────────────

NEW_TOWN_RMSE = {
    "CHOA CHU KANG":   25850,
    "JURONG WEST":     27064,
    "BUKIT BATOK":     27236,
    "SEMBAWANG":       27291,
    "WOODLANDS":       28791,
    "YISHUN":          30311,
    "JURONG EAST":     30635,
    "PUNGGOL":         34446,
    "BUKIT PANJANG":   35608,
    "PASIR RIS":       36010,
    "SENGKANG":        36088,
    "TAMPINES":        36298,
    "HOUGANG":         36393,
    "ANG MO KIO":      39956,
    "BEDOK":           39959,
    "TOA PAYOH":       45540,
    "SERANGOON":       45768,
    "GEYLANG":         47448,
    "KALLANG/WHAMPOA": 49514,
    "CLEMENTI":        49966,
    "BUKIT TIMAH":     50343,
    "BUKIT MERAH":     53977,
    "MARINE PARADE":   54253,
    "CENTRAL AREA":    58720,
    "BISHAN":          59406,
    "QUEENSTOWN":      62507,
}

# Worst 8 (highest RMSE) — for Model Performance tab
WORST_8 = dict(sorted(NEW_TOWN_RMSE.items(), key=lambda x: -x[1])[:8])

# Best 8 (lowest RMSE)
BEST_8 = dict(sorted(NEW_TOWN_RMSE.items(), key=lambda x: x[1])[:8])

DEFAULT_RMSE = 38295


def dict_to_python(d: dict) -> str:
    lines = ["{"]
    for k, v in d.items():
        lines.append(f'    "{k}":{v},')
    lines.append("}")
    return "\n".join(lines)


def update_app():
    with open(APP_PATH, "r") as f:
        content = f.read()

    # 1. Replace TOWN_RMSE dict
    new_rmse_str = "TOWN_RMSE = {\n"
    for k, v in NEW_TOWN_RMSE.items():
        new_rmse_str += f'    "{k}":{v},\n'
    new_rmse_str += "}"

    content = re.sub(
        r"TOWN_RMSE = \{[^}]+\}",
        new_rmse_str,
        content,
        flags=re.DOTALL,
    )

    # 2. Replace DEFAULT_RMSE
    content = re.sub(
        r"DEFAULT_RMSE = \d+",
        f"DEFAULT_RMSE = {DEFAULT_RMSE}",
        content,
    )

    # 3. Replace worst_t dict in Model Performance tab
    new_worst = "worst_t = {\n"
    for k, v in WORST_8.items():
        new_worst += f'        "{k}":{v},\n'
    new_worst += "    }"
    content = re.sub(
        r"worst_t = \{[^}]+\}",
        new_worst,
        content,
        flags=re.DOTALL,
    )

    # 4. Replace best_t dict in Model Performance tab
    new_best = "best_t = {\n"
    for k, v in BEST_8.items():
        new_best += f'        "{k}":{v},\n'
    new_best += "    }"
    content = re.sub(
        r"best_t = \{[^}]+\}",
        new_best,
        content,
        flags=re.DOTALL,
    )

    # 5. Fix TOAPAYOH → TOA PAYOH in TOWNS list and any string references
    content = content.replace('"TOAPAYOH"', '"TOA PAYOH"')

    # 6. Update RMSE figures in About tab and captions
    content = content.replace("RMSE $51,616", "RMSE $38,295")
    content = content.replace("RMSE $51616", "RMSE $38295")
    content = content.replace("R²: 0.94", "R²: 0.967")
    content = content.replace("R²: 0.94", "R²: 0.967")

    with open(APP_PATH, "w") as f:
        f.write(content)

    print("app/main.py updated.")
    print(f"  DEFAULT_RMSE: {DEFAULT_RMSE}")
    print(f"  Worst town: {list(WORST_8.items())[0]}")
    print(f"  Best town:  {list(BEST_8.items())[0]}")
    print(f"  TOAPAYOH → TOA PAYOH: fixed")


if __name__ == "__main__":
    update_app()
