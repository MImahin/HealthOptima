from flask import Flask, render_template, request, redirect, url_for, session
import os
import pandas as pd
import ast
from rapidfuzz import process
import easyocr 
from werkzeug.utils import secure_filename
from analyse import perform_health_analysis


from nutrition import (
    get_food_nutrients_in_grams,
    get_dietary_warnings,
    plot_nutrient_pie_chart_grams
)


base_dir = os.path.abspath(os.path.dirname(__file__))
user_data_path = os.path.join(base_dir, 'user_data', 'user_data.csv')
ingredient_data_path = os.path.join(base_dir, 'updated_ingredients_conditions', 'updated_ingredients_conditions.csv')
demo_user_data_path = os.path.join(base_dir, 'user_data', 'demo_user_data.csv')

ud = pd.read_csv(user_data_path)
fic = pd.read_csv(ingredient_data_path, index_col=0)

class Person:
    def __init__(self, name, id, age, password, conditions, gender, weight, height):
        self.name = name
        self.id = id
        self.age = age
        self.password = password
        self.conditions = conditions
        self.gender = gender
        self.weight = float(weight)  # assuming weight in kg
        self.height = float(height)  # assuming height in cm
        self.bmi = self.calculate_bmi()
        self.bmi_category = self.get_bmi_category()

    def calculate_bmi(self):
        height_m = self.height / 100  # convert cm to meters
        bmi = self.weight / (height_m ** 2)
        return round(bmi, 2)

    def get_bmi_category(self):
        bmi = self.bmi
        if bmi < 18.5:
            return "Underweight"
        elif 18.5 <= bmi < 25:
            return "Normal weight"
        elif 25 <= bmi < 30:
            return "Overweight"
        else:
            return "Obese"

    def add_to_csv(self):
        global ud
        atc = {
            "Username": self.name,
            "ID": self.id,
            "Age": self.age,
            "Password": self.password,
            # Save conditions as a proper list string for correct parsing later
           "Conditions": str(self.conditions), 
            "Gender": self.gender,
            "Weight": self.weight,
            "Height": self.height
        }
        ud = pd.concat([ud, pd.DataFrame([atc])], ignore_index=True)
        ud.to_csv(user_data_path, index=False)

    def search_img(self,img):       
        raw_lines = []
        result = easyocr.Reader(["en"]).readtext(img)
        for (bbox,text,prob) in result:
            if prob >= 0.5:
                raw_lines.append(text)

        text_block = " ".join(raw_lines)
        text = text_block.lower()
        text = text.replace("(", " ").replace(")", " ")
        text = ''.join([c if c.isalpha() or c.isspace() else ' ' for c in text])

        words = text.split()

        def get_phrases(words, max_n=3):
            return [' '.join(words[i:i+n]) for n in range(1, max_n+1) for i in range(len(words)-n+1)]

        phrases = set(get_phrases(words))

        df = pd.read_csv(ingredient_data_path)

        ingredients= df["Food Ingredients"].str.lower().tolist()

        matched = [p for p in phrases if p in ingredients]
        unmatched = [p for p in phrases if p not in ingredients]

        fuzzy_matches = []
        fuzzy_selected = set()
        for item in unmatched:
            match, score, index = process.extractOne(item, ingredients)
            if score >= 89: 
                fuzzy_matches.append((item, match, score))
                fuzzy_selected.add(match)
        all_matched = list(set(matched) | fuzzy_selected)

        result_tuple = self.checkeffect(all_matched)
        return result_tuple


    def checkeffect(self, matchedlist):
        effects = set()
        bad_ingredients = []
        for i in self.conditions:
            for j in matchedlist:
                i = str(i).title()
                j = str(j).capitalize()
                try:
                    value = fic.loc[j, i]
                except KeyError:
                    continue

                if value.lower() == 'bad':
                    bad_ingredients.append(j)
                effects.add(value.lower())
        unique_bad_ingredients = set(bad_ingredients)  # removes duplicates, order not guaranteed
        bad_list_str = "\n- " + "\n- ".join(unique_bad_ingredients)
        if "bad" in effects:
            return "Warning: This food contains ingredients that may not be suitable for your health conditions. Please consult a health professional before consuming. \nHarmful ingredients are:" + bad_list_str,bad_ingredients
        elif 'good' in effects:
            return "This food looks safe and beneficial based on your selected health conditions.", bad_ingredients
        else:
            return "This food is mostly safe, but contains some neutral ingredients. You may consume it in moderation.", bad_ingredients


app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here'  # <-- Change to a secure key

@app.route('/')
def start():
    return render_template('start.html')

@app.route('/account')
def account():   
    return render_template('account.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        id = int(request.form['id'])  # Convert to int
        password = request.form['password']
    
        if id in ud.index and name == ud.at[id, 'Username'] and password == str(ud.at[id, 'Password']):
            conditions = ast.literal_eval(ud.at[id, 'Conditions'])
            gender = ud.at[id, 'Gender']
            weight = ud.at[id, 'Weight']
            height = ud.at[id, 'Height']
            session['user_id'] = id  # Store in session
            person = Person(name, id, ud.at[id, 'Age'], password, conditions, gender, weight, height)
            return redirect(url_for('home', source='login'))
        else:
            return render_template('login.html', error_message="Invalid input")
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    conditions_list = fic.columns.tolist()[3:]
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        password = request.form['password']
        gender = request.form['gender']
        weight = request.form['weight']
        height = request.form['height']
        raw_conditions = request.form.getlist('conditions')
        conditions = [c.strip() for cond in raw_conditions for c in cond.split(',')]

        id = len(ud)
        person = Person(name, id, age, password, conditions, gender, weight, height)
        person.add_to_csv()
        session['user_id'] = id  # Store in session
        return redirect(url_for('home', source='signup'))

    return render_template('signup.html', conditions=conditions_list)

from plots import generate_home_plots  # Add this import
import ast

@app.route('/home')
def home():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user_row = ud.loc[user_id]
    age = user_row['Age']
    gender = user_row['Gender']
    weight = user_row['Weight']

    # Prepare user info for profile card (excluding password & conditions)
    user_info = user_row.to_dict()
    user_info.pop("Password", None)

    # Convert string list of conditions to a Python list, then to a set
    user_conditions = ast.literal_eval(user_row['Conditions'])
    user_conditions = set(user_conditions)

    user_info.pop("Conditions", None)

    # Handle source messages
    source = request.args.get('source', '')
    success_message = None
    if source == 'login':
        success_message = "Login Successful!"
    elif source == 'signup':
        success_message = "Account Created Successfully!"
    # Get plots and warnings — pass user_conditions to highlight bars properly
    plot_data = generate_home_plots(age, gender, weight, user_conditions)
    plots = [img_base64 for img_base64, _ in plot_data]
    warnings = [msg or "" for _, msg in plot_data]


    return render_template(
        'home.html',
        success_message=success_message,
        age=age,
        gender=gender,
        weight=weight,
        plots=plots,
        warnings=warnings,
        user_info=user_info
    )



UPLOAD_FOLDER = os.path.join(base_dir, 'uploaded_images')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'} 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploadimage', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'ingredient-image' not in request.files:
            return render_template('uploadimage.html', message="No file part")
        
        file = request.files['ingredient-image']
        
        if file.filename == '':
            return render_template('uploadimage.html', message="No selected file")
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            return redirect(url_for('result', filename=filename))
        else:
            return render_template('uploadimage.html', message="Invalid file type. Please upload a valid image.")
    
    return render_template('uploadimage.html', message="Upload an image to analyze.")

@app.route('/result')
def result():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))  # redirect if not logged in

    filename = request.args.get('filename')
    if not filename:
        return "No image uploaded", 400

    row = ud.loc[user_id]
    conditions = ast.literal_eval(row['Conditions'])
    person = Person(row['Username'], user_id, row['Age'], row['Password'], conditions,
                    row['Gender'], row['Weight'], row['Height'])
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    result_tuple = person.search_img(filepath)
    result, bad_ingredients = result_tuple

    return render_template('result.html', result=result)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/searchfood', methods=['GET', 'POST'])
def searchfood():
    food_name = ""
    description = ""
    warnings = []
    chart_filename = None
    no_data = False
    ingredients = []

    if request.method == 'POST':
        food_name = request.form['food_name']
        result = get_food_nutrients_in_grams(food_name)

        if result:
            nutrients, description, ingredients = result

            # Generate pie chart
            chart_filename = f"{food_name.replace(' ', '_')}_chart.png"
            chart_folder = os.path.join('static', 'charts')
            os.makedirs(chart_folder, exist_ok=True)

            chart_path = os.path.join(chart_folder, chart_filename)
            plot_nutrient_pie_chart_grams(nutrients, description, chart_path)

            chart_path = f"charts/{chart_filename}"
            warnings = get_dietary_warnings(nutrients)
        else:
            no_data = True
            chart_path = None

        return render_template(
            'searchfood.html',
            food_name=food_name,
            description=description,
            warnings=warnings,
            chart_path=chart_path,
            no_data=no_data,
            ingredients=ingredients
        )

    return render_template(
        'searchfood.html',
        food_name=food_name,
        description=description,
        warnings=warnings,
        chart_path=chart_filename,
        no_data=no_data,
        ingredients=ingredients
    )


@app.route('/analysehealth', methods=['GET', 'POST'])
def analysehealth():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    row = ud.loc[user_id]
    # Base user info without measurements
    user_info = {
        "Username": row['Username'],
        "ID": user_id,
        "Age": row['Age'],
        "Password": row['Password'],
        "Conditions": row['Conditions'],
        "Gender": row['Gender'],
        "Weight": row['Weight'],
        "Height": row['Height']
    }

    if request.method == 'POST':
        # Get measurements from submitted form, convert to float or fallback to None
        try:
            waist = float(request.form.get('waist', ''))
        except ValueError:
            waist = None
        try:
            neck = float(request.form.get('neck', ''))
        except ValueError:
            neck = None
        try:
            hip = float(request.form.get('hip', ''))
        except ValueError:
            hip = None

        # Add measurements to user_info only if provided
        if waist:
            user_info["Waist"] = waist
        if neck:
            user_info["Neck"] = neck
        if hip:
            user_info["Hip"] = hip

        plot1, plot2, plot3, metrics = perform_health_analysis(demo_user_data_path, user_info)

        return render_template(
            'analysehealth.html',
            plot1=plot1,
            plot2=plot2,
            plot3=plot3,
            metrics=metrics,
            show_form=False
        )
    
    # GET request - show input form for waist, neck, hip
    return render_template(
        'analysehealth.html',
        show_form=True,
        user_info=user_info
    )
























if __name__ == '__main__':
    app.run(debug=True)
