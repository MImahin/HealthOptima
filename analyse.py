import pandas as pd
import matplotlib.pyplot as plt
import math
import ast
import os

def classify_bmi(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 24.9:
        return "Normal"
    elif 25 <= bmi < 29.9:
        return "Overweight"
    else:
        return "Obese"

def body_fat_category(gender, bf):
    if gender == "Male":
        if 2 <= bf <= 5:
            return "Essential fat"
        elif 6 <= bf <= 13:
            return "Athletes"
        elif 14 <= bf <= 17:
            return "Fitness"
        elif 18 <= bf <= 24:
            return "Average"
        elif bf >= 25:
            return "Obese"
        else:
            return "Below essential fat"
    else:
        if 10 <= bf <= 13:
            return "Essential fat"
        elif 14 <= bf <= 20:
            return "Athletes"
        elif 21 <= bf <= 24:
            return "Fitness"
        elif 25 <= bf <= 31:
            return "Average"
        elif bf >= 32:
            return "Obese"
        else:
            return "Below essential fat"

def plot_bmi_category_bar(group, title, filename):
    counts = group["BMI_Category"].value_counts(normalize=True) * 100
    categories = ["Underweight", "Normal", "Overweight", "Obese"]
    percentages = [counts.get(cat, 0) for cat in categories]

    fig, ax = plt.subplots()
    bars = ax.bar(categories, percentages, color=['#5DADE2', '#58D68D', '#F4D03F', '#E74C3C'])
    ax.set_ylabel('Percentage (%)')
    ax.set_ylim(0, 100)
    ax.set_title(title)
    ax.bar_label(bars, fmt='%.1f%%')

    plot_path = os.path.join("static", "charts", filename)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    return f"charts/{filename}"

def perform_health_analysis(user_data_path, user_info):
    df = pd.read_csv(user_data_path)
    df = pd.concat([df, pd.DataFrame([user_info])], ignore_index=True)

    df["Height_m"] = df["Height"] / 100
    df["BMI"] = df["Weight"] / (df["Height_m"] ** 2)
    df["BMI_Category"] = df["BMI"].apply(classify_bmi)

    age = user_info["Age"]
    gender = user_info["Gender"]
    conditions = ast.literal_eval(user_info["Conditions"])

    age_group = df[df["Age"] == age]
    gender_group = df[df["Gender"] == gender]

    def shares_condition(cond_str):
        try:
            cond_list = ast.literal_eval(cond_str)
        except Exception:
            return False
        return len(set(cond_list) & set(conditions)) > 0

    condition_group = df[df["Conditions"].apply(shares_condition)]

    os.makedirs(os.path.join("static", "charts"), exist_ok=True)

    plot1 = plot_bmi_category_bar(age_group, f"BMI by Age {age}", "age_group_plot.png")
    plot2 = plot_bmi_category_bar(gender_group, f"BMI by Gender: {gender}", "gender_group_plot.png")
    plot3 = plot_bmi_category_bar(condition_group, "BMI by Similar Conditions", "condition_group_plot.png")

    # TDEE / BMR / Body Fat
    weight = user_info["Weight"]
    height = user_info["Height"]
    age = user_info["Age"]
    gender = user_info["Gender"]

    # Get measurements dynamically, fallback to defaults if missing
    waist = user_info.get("Waist", 85)
    neck = user_info.get("Neck", 38)
    hip = user_info.get("Hip", 100)

    # Convert to proper numeric types
    weight = float(user_info["Weight"])
    height = float(user_info["Height"])
    age = int(user_info["Age"])

    waist = float(user_info.get("Waist", 85))
    neck = float(user_info.get("Neck", 38))
    hip = float(user_info.get("Hip", 100))


    bmi = weight / ((height / 100) ** 2)
    if gender == "Male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
        body_fat = 86.010 * math.log10(waist - neck) - 70.041 * math.log10(height) + 36.76
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
        body_fat = 163.205 * math.log10(waist + hip - neck) - 97.684 * math.log10(height) + 78.387

    tdee = bmr * 1.375  # activity_level fixed here

    bf_cat = body_fat_category(gender, body_fat)

    if bmi < 18.5:
        cal_advice = f"Underweight: Gain weight by consuming {tdee + 250:.0f} to {tdee + 500:.0f} kcal/day."
    elif 18.5 <= bmi < 24.9:
        cal_advice = f"Normal BMI: Maintain weight by consuming around {tdee:.0f} kcal/day."
    else:
        cal_advice = f"Overweight/Obese: Lose weight by consuming {tdee - 1000:.0f} to {tdee - 500:.0f} kcal/day."
    if bmi < 18.5:
        bmi_category = "Underweight"
    elif 18.5 <= bmi < 24.9:
        bmi_category = "Normal weight"
    elif 24.9 <= bmi < 29.9:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obese"

# Now format BMI string with category appended
    bmi_str = f"{bmi:.2f} ({bmi_category})"

    text_summary = {
        "BMI": bmi_str,
        "BMR": f"{bmr:.2f} kcal/day",
        "TDEE": f"{tdee:.2f} kcal/day",
        "Body Fat %": f"{body_fat:.2f}%",
        "Body Fat Category": bf_cat,
        "Calorie Advice": cal_advice
    }

    return plot1, plot2, plot3, text_summary
