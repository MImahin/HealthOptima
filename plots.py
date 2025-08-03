import pandas as pd
import matplotlib.pyplot as plt
import ast
from io import BytesIO
import base64
import matplotlib.patches as mpatches


demo_user_data_path = 'user_data/demo_user_data.csv'
MIN_DATA_COUNT = 10

def load_latest_df():
    df = pd.read_csv(demo_user_data_path)
    df['Conditions'] = df['Conditions'].apply(ast.literal_eval)
    return df

def generate_condition_plot(filtered_df, title, user_conditions):
    
    
    if len(filtered_df) < MIN_DATA_COUNT:
        return None, f"[Skipped] Not enough data for: {title} (only {len(filtered_df)+1} users)"

    condition_counts = filtered_df['Conditions'].explode().value_counts()
    condition_percent = (condition_counts / len(filtered_df)) * 100
    condition_percent = condition_percent.sort_values(ascending=True)

    plt.figure(figsize=(10, 6))
    colors = ['yellow' if cond in user_conditions else 'skyblue' for cond in condition_percent.index]
    condition_percent.plot(kind='barh', color=colors)
    plt.xlabel("Percentage of Users (%)")
    plt.title(title)

    for i, v in enumerate(condition_percent):
        plt.text(v + 0.5, i, f'{v:.1f}%', va='center')

    
    yellow_patch = mpatches.Patch(color='yellow', label='Your Condition')
    blue_patch = mpatches.Patch(color='skyblue', label='Other Conditions')
    plt.legend(handles=[yellow_patch, blue_patch], loc='lower right')

    plt.tight_layout()
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    encoded = base64.b64encode(img.getvalue()).decode()
    return f"data:image/png;base64,{encoded}", None

def generate_home_plots(age, gender, weight, user_conditions):
   

    df = load_latest_df() 

    plots = []
    
    same_age_df = df[df['Age'].astype(int) == int(age)]

    age_plot, age_msg = generate_condition_plot(same_age_df, f"Conditions for Users with Age = {age}", user_conditions)
    plots.append((age_plot, age_msg))

    same_gender_df = df[df['Gender'].str.lower() == gender.lower()]
    gender_plot, gender_msg = generate_condition_plot(same_gender_df, f"Conditions for Users with Gender = {gender}", user_conditions)
    plots.append((gender_plot, gender_msg))

    same_weight_df = df[df['Weight'] == weight]
    weight_plot, weight_msg = generate_condition_plot(same_weight_df, f"Conditions for Users with Weight = {weight}", user_conditions)
    plots.append((weight_plot, weight_msg))
    

    return plots

