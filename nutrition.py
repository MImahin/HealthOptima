import requests

import matplotlib
matplotlib.use('Agg')  #  Use a non-GUI backend suitable for web apps

import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os
load_dotenv()

USDA_API_KEY = os.getenv("USDA_API_KEY")

def get_food_nutrients_in_grams(food_name, api_key=USDA_API_KEY):
    search_url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    search_params = {
        "api_key": api_key,
        "query": food_name,
        "pageSize": 5,
    }
    search_response = requests.get(search_url, params=search_params)
    search_data = search_response.json()

    foods = search_data.get("foods", [])
    food = None
    for item in foods:
        if item.get("dataType") != "Branded":
            food = item
            break
    if not food and foods:
        food = foods[0]

    if not food:
        return None

    fdc_id = food["fdcId"]
    detail_url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    detail_params = {"api_key": api_key}
    detail_response = requests.get(detail_url, params=detail_params)
    detail_data = detail_response.json()

    nutrients_raw = detail_data.get("foodNutrients", [])
    nutrients_g = {}

    for nutrient in nutrients_raw:
        name = nutrient.get("nutrient", {}).get("name") or nutrient.get("nutrientName", "")
        amount = nutrient.get("amount") or nutrient.get("value", 0)
        unit = nutrient.get("nutrient", {}).get("unitName") or nutrient.get("unitName", "")

        if unit == "g":
            amount_g = amount
        elif unit == "mg":
            amount_g = amount / 1000
        else:
            continue

        if amount_g > 0:
            nutrients_g[name] = nutrients_g.get(name, 0) + amount_g

    if not nutrients_g:
        return None

    # Extract ingredients info if available (string)
    ingredients_info = detail_data.get("ingredients", None)

    return nutrients_g, food.get("description", food_name), ingredients_info


def get_value_by_partial_key(nutrients, keyword):
    for key, value in nutrients.items():
        if keyword.lower() in key.lower():
            return value
    return 0


def get_dietary_warnings(nutrients):
    warnings = []

    if get_value_by_partial_key(nutrients, "Sodium") >= 0.3:
        warnings.append("⚠️ High sodium — caution if you have high blood pressure.")

    if get_value_by_partial_key(nutrients, "Total Sugars") >= 10:
        warnings.append("⚠️ High sugar — may not be ideal for diabetics.")

    if get_value_by_partial_key(nutrients, "Cholesterol") >= 0.06:
        warnings.append("⚠️ High cholesterol — limit if at risk of heart disease.")

    if get_value_by_partial_key(nutrients, "Fatty acids, total saturated") >= 3:
        warnings.append("⚠️ High saturated fat — linked to heart disease risk.")

    fiber = get_value_by_partial_key(nutrients, "Fiber")
    if fiber < 0.002:
        warnings.append("ℹ️ Extremely low fiber — not supportive of digestion.")
    elif fiber < 2:
        warnings.append("ℹ️ Low fiber — less filling, may not support gut health.")

    if not warnings:
        warnings.append("✅ No major red flags found in nutrient levels.")

    return warnings


def plot_nutrient_pie_chart_grams(nutrients_g, food_name, save_path):
    main_nutrients = {k: v for k, v in nutrients_g.items() if v > 1}
    other_total = sum(v for k, v in nutrients_g.items() if v <= 1)
    if other_total > 0:
        main_nutrients["Other"] = other_total

    if not main_nutrients:
        return

    labels = list(main_nutrients.keys())
    sizes = list(main_nutrients.values())

    def autopct_func(pct):
        return f'{pct:.1f}%' if pct >= 3 else ''

    display_labels = [label if (val / sum(sizes)) * 100 >= 3 else '' for label, val in zip(labels, sizes)]

    fig, ax = plt.subplots(figsize=(10, 10), dpi=150)  # Bigger figure and higher DPI
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=display_labels,
        autopct=autopct_func,
        startangle=90,
        textprops={'fontsize': 12}
    )
    ax.axis('equal')
    ax.legend(
    [f'{k}: {v:.2f}g' for k, v in main_nutrients.items()],
    loc='center left',              # Anchor from the left of the legend
    bbox_to_anchor=(1.05, 0.5),     # Push legend OUTSIDE to the right
    fontsize=14,
    frameon=False
)


    plt.title(f"Nutrient Distribution in {food_name.title()}", fontsize=16)
    plt.savefig(save_path, bbox_inches='tight', dpi=150)  # Save with higher DPI
    plt.close()


if __name__ == "__main__":
    API_KEY = USDA_API_KEY
    food_name_input = input("Enter a food name: ").strip()

    result = get_food_nutrients_in_grams(food_name_input, API_KEY)
    if result:
        nutrients_g, food_description, ingredients = result
        print(f"Description: {food_description}")
        print(f"Ingredients: {ingredients or 'No ingredients info available'}\n")
        warnings = get_dietary_warnings(nutrients_g)
        print("Dietary Warnings:")
        for w in warnings:
            print(w)
        
        plot_nutrient_pie_chart_grams(nutrients_g, food_description, "nutrient_chart.png")
        print("\nPie chart saved as 'nutrient_chart.png'")
    else:
        print("No data found.")
