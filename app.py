from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///health_tracker.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    height = db.Column(db.Float)
    weights = db.relationship('Weight', backref='user', lazy=True)
    exercises = db.relationship('Exercise', backref='user', lazy=True)
    water_logs = db.relationship('WaterLog', backref='user', lazy=True)
    goals = db.relationship('Goals', backref='user', lazy=True)
    nutrition_logs = db.relationship('NutritionLog', backref='user', lazy=True)
    reminders = db.relationship('Reminder', backref='user', lazy=True)

class Weight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(80), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    calories = db.Column(db.Integer)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class WaterLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Integer, nullable=False)  # in ml
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Goals(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_weight = db.Column(db.Float)
    target_exercise_minutes = db.Column(db.Integer)  # daily target
    target_water_ml = db.Column(db.Integer)  # daily target in ml
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    target_date = db.Column(db.DateTime)
    active = db.Column(db.Boolean, default=True)

class NutritionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_type = db.Column(db.String(50), nullable=False)  # breakfast, lunch, dinner, snack
    food_name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    protein = db.Column(db.Float)  # in grams
    carbs = db.Column(db.Float)    # in grams
    fat = db.Column(db.Float)      # in grams
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    portion_size = db.Column(db.Float)  # in grams or ml
    notes = db.Column(db.String(200))

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    reminder_type = db.Column(db.String(50), nullable=False)  # water, exercise, meal, weight, medication
    frequency = db.Column(db.String(50), nullable=False)  # daily, weekly, custom
    time = db.Column(db.Time, nullable=False)  # For daily/custom reminders
    days = db.Column(db.String(100))  # JSON string of days for weekly reminders
    active = db.Column(db.Boolean, default=True)
    last_triggered = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home page
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.utcnow().date()
    last_weight = Weight.query.filter_by(user_id=current_user.id).order_by(Weight.date.desc()).first()
    last_exercise = Exercise.query.filter_by(user_id=current_user.id).order_by(Exercise.date.desc()).first()
    last_water = WaterLog.query.filter_by(user_id=current_user.id).order_by(WaterLog.date.desc()).first()
    
    # Get last nutrition log regardless of date
    last_nutrition = NutritionLog.query.filter_by(user_id=current_user.id).order_by(NutritionLog.date.desc()).first()

    return render_template('dashboard.html', 
                         last_weight=last_weight,
                         last_exercise=last_exercise,
                         last_water=last_water,
                         last_nutrition=last_nutrition)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            password_hash=generate_password_hash(request.form.get('password')),
            height=float(request.form.get('height', 0))
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Add weight
@app.route('/add_weight', methods=['POST'])
@login_required
def add_weight():
    weight = float(request.form.get('weight'))
    weight_log = Weight(weight=weight, user_id=current_user.id)
    db.session.add(weight_log)
    db.session.commit()
    flash('Weight recorded successfully!', 'weight')
    return redirect(url_for('dashboard'))

# Add exercise
@app.route('/add_exercise', methods=['POST'])
@login_required
def add_exercise():
    exercise = Exercise(
        type=request.form.get('type'),
        duration=int(request.form.get('duration')),
        calories=int(request.form.get('calories', 0)),
        user_id=current_user.id
    )
    db.session.add(exercise)
    db.session.commit()
    flash('Exercise recorded successfully!', 'exercise')
    return redirect(url_for('dashboard'))

# Add water intake
@app.route('/add_water', methods=['POST'])
@login_required
def add_water():
    water_log = WaterLog(
        amount=int(request.form.get('amount')),
        user_id=current_user.id
    )
    db.session.add(water_log)
    db.session.commit()
    flash('Water intake recorded successfully!', 'water')
    return redirect(url_for('dashboard'))

def get_user_statistics(user_id):
    """Calculate user statistics for the last 30 days"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Weight statistics
    weights = Weight.query.filter(
        Weight.user_id == user_id,
        Weight.date >= start_date,
        Weight.date <= end_date
    ).order_by(Weight.date.asc()).all()
    
    weight_dates = [w.date.strftime('%Y-%m-%d') for w in weights]
    weight_data = [w.weight for w in weights]
    
    avg_weight = sum(weight_data) / len(weight_data) if weight_data else 0
    weight_change = weight_data[-1] - weight_data[0] if len(weight_data) > 1 else 0
    
    # Exercise statistics
    exercises = Exercise.query.filter(
        Exercise.user_id == user_id,
        Exercise.date >= start_date,
        Exercise.date <= end_date
    ).order_by(Exercise.date.asc()).all()
    
    exercise_dates = []
    exercise_durations = []
    total_calories = 0
    total_exercise = 0
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        day_exercises = [e for e in exercises if e.date.date() == current_date.date()]
        
        duration_sum = sum(e.duration for e in day_exercises)
        total_exercise += duration_sum
        total_calories += sum(e.calories or 0 for e in day_exercises)
        
        exercise_dates.append(date_str)
        exercise_durations.append(duration_sum)
        
        current_date += timedelta(days=1)
    
    # Water intake statistics
    water_logs = WaterLog.query.filter(
        WaterLog.user_id == user_id,
        WaterLog.date >= start_date,
        WaterLog.date <= end_date
    ).order_by(WaterLog.date.asc()).all()
    
    water_dates = []
    water_amounts = []
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        day_logs = [w for w in water_logs if w.date.date() == current_date.date()]
        
        water_dates.append(date_str)
        water_amounts.append(day_logs[-1].amount if day_logs else 0)
        
        current_date += timedelta(days=1)
    
    return {
        'weight_dates': weight_dates,
        'weight_data': weight_data,
        'exercise_dates': exercise_dates,
        'exercise_durations': exercise_durations,
        'water_dates': water_dates,
        'water_amounts': water_amounts,
        'stats': {
            'avg_weight': avg_weight,
            'weight_change': weight_change,
            'total_exercise': total_exercise,
            'total_calories': total_calories
        }
    }

@app.route('/statistics')
@login_required
def statistics():
    stats_data = get_user_statistics(current_user.id)
    return render_template('statistics.html', 
                         weight_dates=stats_data['weight_dates'],
                         weight_data=stats_data['weight_data'],
                         exercise_dates=stats_data['exercise_dates'],
                         exercise_durations=stats_data['exercise_durations'],
                         water_dates=stats_data['water_dates'],
                         water_amounts=stats_data['water_amounts'],
                         stats=stats_data['stats'])

@app.route('/api/goals', methods=['POST'])
@login_required
def create_goal():
    data = request.get_json()
    
    # Deactivate any existing active goals
    active_goals = Goals.query.filter_by(user_id=current_user.id, active=True).all()
    for goal in active_goals:
        goal.active = False
    
    new_goal = Goals(
        user_id=current_user.id,
        target_weight=data.get('target_weight'),
        target_exercise_minutes=data.get('target_exercise_minutes'),
        target_water_ml=data.get('target_water_ml'),
        start_date=datetime.now(),
        target_date=datetime.strptime(data['target_date'], '%Y-%m-%d'),
        active=True
    )
    
    db.session.add(new_goal)
    db.session.commit()
    flash('New goal set successfully!', 'goal')
    
    return jsonify({
        'id': new_goal.id,
        'target_weight': new_goal.target_weight,
        'target_exercise_minutes': new_goal.target_exercise_minutes,
        'target_water_ml': new_goal.target_water_ml,
        'start_date': new_goal.start_date.strftime('%Y-%m-%d'),
        'target_date': new_goal.target_date.strftime('%Y-%m-%d'),
        'active': new_goal.active
    }), 201

@app.route('/api/goals/active', methods=['GET'])
@login_required
def get_active_goals():
    active_goal = Goals.query.filter_by(user_id=current_user.id, active=True).first()
    
    if not active_goal:
        return jsonify({'message': 'No active goals found'}), 404
        
    return jsonify({
        'id': active_goal.id,
        'target_weight': active_goal.target_weight,
        'target_exercise_minutes': active_goal.target_exercise_minutes,
        'target_water_ml': active_goal.target_water_ml,
        'start_date': active_goal.start_date.strftime('%Y-%m-%d'),
        'target_date': active_goal.target_date.strftime('%Y-%m-%d'),
        'active': active_goal.active
    })

@app.route('/api/goals/<int:goal_id>', methods=['PUT'])
@login_required
def update_goal(goal_id):
    goal = Goals.query.get_or_404(goal_id)
    
    if goal.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    
    if 'target_weight' in data:
        goal.target_weight = data['target_weight']
    if 'target_exercise_minutes' in data:
        goal.target_exercise_minutes = data['target_exercise_minutes']
    if 'target_water_ml' in data:
        goal.target_water_ml = data['target_water_ml']
    if 'target_date' in data:
        goal.target_date = datetime.strptime(data['target_date'], '%Y-%m-%d')
    if 'active' in data:
        if data['active']:
            # Deactivate other active goals
            active_goals = Goals.query.filter_by(user_id=current_user.id, active=True).all()
            for active_goal in active_goals:
                active_goal.active = False
        goal.active = data['active']
    
    db.session.commit()
    
    return jsonify({
        'id': goal.id,
        'target_weight': goal.target_weight,
        'target_exercise_minutes': goal.target_exercise_minutes,
        'target_water_ml': goal.target_water_ml,
        'start_date': goal.start_date.strftime('%Y-%m-%d'),
        'target_date': goal.target_date.strftime('%Y-%m-%d'),
        'active': goal.active
    })

@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    goal = Goals.query.get_or_404(goal_id)
    
    if goal.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    db.session.delete(goal)
    db.session.commit()
    
    return '', 204

@app.route('/api/nutrition', methods=['POST'])
@login_required
def add_nutrition():
    data = request.get_json()
    print("Received nutrition data:", data)  # Debug print
    
    try:
        nutrition_log = NutritionLog(
            user_id=current_user.id,
            meal_type=data['meal_type'],
            food_name=data['food_name'],
            calories=data['calories'],
            protein=data.get('protein'),
            carbs=data.get('carbs'),
            fat=data.get('fat'),
            portion_size=data.get('portion_size'),
            notes=data.get('notes'),
            date=datetime.strptime(data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), '%Y-%m-%d %H:%M:%S')
        )
        
        db.session.add(nutrition_log)
        db.session.commit()
        flash('Meal logged successfully!', 'nutrition')
        
        return jsonify({
            'id': nutrition_log.id,
            'meal_type': nutrition_log.meal_type,
            'food_name': nutrition_log.food_name,
            'calories': nutrition_log.calories,
            'protein': nutrition_log.protein,
            'carbs': nutrition_log.carbs,
            'fat': nutrition_log.fat,
            'portion_size': nutrition_log.portion_size,
            'notes': nutrition_log.notes,
            'date': nutrition_log.date.strftime('%Y-%m-%d %H:%M:%S')
        }), 201
    except Exception as e:
        print("Error creating nutrition log:", str(e))  # Debug print
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/nutrition/daily/<date>', methods=['GET'])
@login_required
def get_daily_nutrition(date):
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d')
        next_date = target_date + timedelta(days=1)
        
        logs = NutritionLog.query.filter(
            NutritionLog.user_id == current_user.id,
            NutritionLog.date >= target_date,
            NutritionLog.date < next_date
        ).order_by(NutritionLog.date.asc()).all()
        
        daily_totals = {
            'total_calories': sum(log.calories for log in logs),
            'total_protein': sum(log.protein or 0 for log in logs),
            'total_carbs': sum(log.carbs or 0 for log in logs),
            'total_fat': sum(log.fat or 0 for log in logs)
        }
        
        meals = {}
        for log in logs:
            if log.meal_type not in meals:
                meals[log.meal_type] = []
            meals[log.meal_type].append({
                'id': log.id,
                'food_name': log.food_name,
                'calories': log.calories,
                'protein': log.protein,
                'carbs': log.carbs,
                'fat': log.fat,
                'portion_size': log.portion_size,
                'notes': log.notes,
                'date': log.date.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'date': date,
            'daily_totals': daily_totals,
            'meals': meals
        })
        
    except ValueError:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

@app.route('/api/nutrition/<int:log_id>', methods=['PUT'])
@login_required
def update_nutrition(log_id):
    log = NutritionLog.query.get_or_404(log_id)
    
    if log.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if 'meal_type' in data:
        log.meal_type = data['meal_type']
    if 'food_name' in data:
        log.food_name = data['food_name']
    if 'calories' in data:
        log.calories = data['calories']
    if 'protein' in data:
        log.protein = data['protein']
    if 'carbs' in data:
        log.carbs = data['carbs']
    if 'fat' in data:
        log.fat = data['fat']
    if 'portion_size' in data:
        log.portion_size = data['portion_size']
    if 'notes' in data:
        log.notes = data['notes']
    if 'date' in data:
        log.date = datetime.strptime(data['date'], '%Y-%m-%d %H:%M:%S')
    
    db.session.commit()
    flash('Meal updated successfully!', 'nutrition')
    
    return jsonify({
        'id': log.id,
        'meal_type': log.meal_type,
        'food_name': log.food_name,
        'calories': log.calories,
        'protein': log.protein,
        'carbs': log.carbs,
        'fat': log.fat,
        'portion_size': log.portion_size,
        'notes': log.notes,
        'date': log.date.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/nutrition/<int:log_id>', methods=['DELETE'])
@login_required
def delete_nutrition(log_id):
    log = NutritionLog.query.get_or_404(log_id)
    
    if log.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    db.session.delete(log)
    db.session.commit()
    flash('Meal deleted successfully!', 'nutrition')
    
    return '', 204

def calculate_bmi(weight, height):
    """Calculate Body Mass Index (BMI)"""
    if height <= 0 or weight <= 0:
        return 0
    return weight / ((height/100) ** 2)

def get_bmi_category(bmi):
    """Get BMI category"""
    if bmi < 18.5:
        return "Zayıf"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Fazla Kilolu"
    else:
        return "Obez"

def calculate_bmr(weight, height, age, gender):
    """Calculate Basal Metabolic Rate (BMR) using Harris-Benedict equation"""
    if gender.lower() == 'male':
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)

def calculate_daily_calories(bmr, activity_level):
    """Calculate daily calorie needs based on activity level"""
    activity_multipliers = {
        'sedentary': 1.2,      # Little or no exercise
        'light': 1.375,        # Light exercise/sports 1-3 days/week
        'moderate': 1.55,      # Moderate exercise/sports 3-5 days/week
        'active': 1.725,       # Hard exercise/sports 6-7 days/week
        'very_active': 1.9     # Very hard exercise/sports & physical job
    }
    return bmr * activity_multipliers.get(activity_level, 1.2)

def calculate_ideal_weight_range(height, gender):
    """Calculate ideal weight range based on height"""
    if gender.lower() == 'male':
        ideal_weight = (height - 100) - ((height - 100) * 0.10)
    else:
        ideal_weight = (height - 100) - ((height - 100) * 0.15)
    
    return {
        'min': round(ideal_weight * 0.90, 1),
        'max': round(ideal_weight * 1.10, 1)
    }

@app.route('/api/health-metrics', methods=['POST'])
@login_required
def get_health_metrics():
    data = request.get_json()
    weight = data.get('weight')
    height = current_user.height
    age = data.get('age')
    gender = data.get('gender')
    activity_level = data.get('activity_level', 'sedentary')
    
    if not all([weight, height, age, gender]):
        return jsonify({'message': 'Missing required parameters'}), 400
    
    bmi = calculate_bmi(weight, height)
    bmr = calculate_bmr(weight, height, age, gender)
    daily_calories = calculate_daily_calories(bmr, activity_level)
    ideal_weight = calculate_ideal_weight_range(height, gender)
    
    return jsonify({
        'bmi': {
            'value': round(bmi, 1),
            'category': get_bmi_category(bmi)
        },
        'bmr': round(bmr),
        'daily_calories': round(daily_calories),
        'ideal_weight_range': ideal_weight,
        'current_stats': {
            'weight': weight,
            'height': height,
            'age': age,
            'gender': gender,
            'activity_level': activity_level
        }
    })

def calculate_progress_percentage(start_value, current_value, target_value):
    """Calculate progress percentage towards a goal"""
    if start_value == target_value:
        return 100 if current_value == target_value else 0
    progress = (current_value - start_value) / (target_value - start_value) * 100
    return min(max(0, progress), 100)

def get_trend_analysis(data_points):
    """Analyze trend from a list of data points"""
    if not data_points or len(data_points) < 2:
        return "Yeterli veri yok"
    
    start = data_points[0]
    end = data_points[-1]
    change = end - start
    
    if abs(change) < 0.001:
        return "Sabit"
    return "Artış" if change > 0 else "Azalış"

def generate_health_report(user_id, start_date=None, end_date=None):
    """Generate comprehensive health report"""
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    user = User.query.get(user_id)
    active_goal = Goals.query.filter_by(user_id=user_id, active=True).first()

    # Weight Analysis
    weights = Weight.query.filter(
        Weight.user_id == user_id,
        Weight.date >= start_date,
        Weight.date <= end_date
    ).order_by(Weight.date.asc()).all()

    weight_data = {
        'values': [w.weight for w in weights],
        'dates': [w.date.strftime('%Y-%m-%d') for w in weights],
        'trend': get_trend_analysis([w.weight for w in weights]) if weights else "Veri yok",
        'average': sum([w.weight for w in weights]) / len(weights) if weights else 0,
        'total_change': weights[-1].weight - weights[0].weight if len(weights) > 1 else 0
    }

    # Exercise Analysis
    exercises = Exercise.query.filter(
        Exercise.user_id == user_id,
        Exercise.date >= start_date,
        Exercise.date <= end_date
    ).order_by(Exercise.date.asc()).all()

    exercise_data = {
        'total_minutes': sum(e.duration for e in exercises),
        'total_calories': sum(e.calories or 0 for e in exercises),
        'average_daily_minutes': sum(e.duration for e in exercises) / ((end_date - start_date).days or 1),
        'most_common_type': max(
            [(e.type, sum(1 for ex in exercises if ex.type == e.type)) for e in exercises],
            key=lambda x: x[1]
        )[0] if exercises else None
    }

    # Water Intake Analysis
    water_logs = WaterLog.query.filter(
        WaterLog.user_id == user_id,
        WaterLog.date >= start_date,
        WaterLog.date <= end_date
    ).order_by(WaterLog.date.asc()).all()

    water_data = {
        'total_intake': sum(w.amount for w in water_logs),
        'average_daily_intake': sum(w.amount for w in water_logs) / ((end_date - start_date).days or 1),
        'trend': get_trend_analysis([w.amount for w in water_logs]) if water_logs else "Veri yok"
    }

    # Nutrition Analysis
    nutrition_logs = NutritionLog.query.filter(
        NutritionLog.user_id == user_id,
        NutritionLog.date >= start_date,
        NutritionLog.date <= end_date
    ).order_by(NutritionLog.date.asc()).all()

    nutrition_data = {
        'average_daily_calories': sum(n.calories for n in nutrition_logs) / ((end_date - start_date).days or 1),
        'average_macros': {
            'protein': sum(n.protein or 0 for n in nutrition_logs) / ((end_date - start_date).days or 1),
            'carbs': sum(n.carbs or 0 for n in nutrition_logs) / ((end_date - start_date).days or 1),
            'fat': sum(n.fat or 0 for n in nutrition_logs) / ((end_date - start_date).days or 1)
        },
        'meal_distribution': {
            meal_type: len([n for n in nutrition_logs if n.meal_type == meal_type])
            for meal_type in set(n.meal_type for n in nutrition_logs)
        }
    }

    # Goal Progress
    goal_progress = {}
    if active_goal and weights:
        if active_goal.target_weight:
            goal_progress['weight'] = {
                'current': weights[-1].weight,
                'target': active_goal.target_weight,
                'progress': calculate_progress_percentage(weights[0].weight, weights[-1].weight, active_goal.target_weight)
            }
        
        if active_goal.target_exercise_minutes:
            goal_progress['exercise'] = {
                'current': exercise_data['average_daily_minutes'],
                'target': active_goal.target_exercise_minutes,
                'progress': calculate_progress_percentage(0, exercise_data['average_daily_minutes'], active_goal.target_exercise_minutes)
            }
        
        if active_goal.target_water_ml:
            goal_progress['water'] = {
                'current': water_data['average_daily_intake'],
                'target': active_goal.target_water_ml,
                'progress': calculate_progress_percentage(0, water_data['average_daily_intake'], active_goal.target_water_ml)
            }

    return {
        'period': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_days': (end_date - start_date).days
        },
        'weight_analysis': weight_data,
        'exercise_analysis': exercise_data,
        'water_analysis': water_data,
        'nutrition_analysis': nutrition_data,
        'goal_progress': goal_progress
    }

@app.route('/api/reports', methods=['GET'])
@login_required
def get_health_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        report = generate_health_report(current_user.id, start_date, end_date)
        return jsonify(report)
        
    except ValueError:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400

@app.route('/api/reminders', methods=['POST'])
@login_required
def create_reminder():
    data = request.get_json()
    
    # Parse time from string
    reminder_time = datetime.strptime(data['time'], '%H:%M').time()
    
    # Parse days for weekly reminders
    days_json = None
    if data.get('frequency') == 'weekly' and data.get('days'):
        days_json = json.dumps(data['days'])
    
    reminder = Reminder(
        user_id=current_user.id,
        title=data['title'],
        description=data.get('description'),
        reminder_type=data['reminder_type'],
        frequency=data['frequency'],
        time=reminder_time,
        days=days_json,
        active=True
    )
    
    db.session.add(reminder)
    db.session.commit()
    
    return jsonify({
        'id': reminder.id,
        'title': reminder.title,
        'description': reminder.description,
        'reminder_type': reminder.reminder_type,
        'frequency': reminder.frequency,
        'time': reminder.time.strftime('%H:%M'),
        'days': json.loads(reminder.days) if reminder.days else None,
        'active': reminder.active,
        'created_at': reminder.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }), 201

@app.route('/api/reminders', methods=['GET'])
@login_required
def get_reminders():
    reminders = Reminder.query.filter_by(user_id=current_user.id).all()
    
    return jsonify([{
        'id': r.id,
        'title': r.title,
        'description': r.description,
        'reminder_type': r.reminder_type,
        'frequency': r.frequency,
        'time': r.time.strftime('%H:%M'),
        'days': json.loads(r.days) if r.days else None,
        'active': r.active,
        'last_triggered': r.last_triggered.strftime('%Y-%m-%d %H:%M:%S') if r.last_triggered else None,
        'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for r in reminders])

@app.route('/api/reminders/<int:reminder_id>', methods=['PUT'])
@login_required
def update_reminder(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    
    if reminder.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if 'title' in data:
        reminder.title = data['title']
    if 'description' in data:
        reminder.description = data['description']
    if 'reminder_type' in data:
        reminder.reminder_type = data['reminder_type']
    if 'frequency' in data:
        reminder.frequency = data['frequency']
    if 'time' in data:
        reminder.time = datetime.strptime(data['time'], '%H:%M').time()
    if 'days' in data:
        reminder.days = json.dumps(data['days']) if data['days'] else None
    if 'active' in data:
        reminder.active = data['active']
    
    db.session.commit()
    
    return jsonify({
        'id': reminder.id,
        'title': reminder.title,
        'description': reminder.description,
        'reminder_type': reminder.reminder_type,
        'frequency': reminder.frequency,
        'time': reminder.time.strftime('%H:%M'),
        'days': json.loads(reminder.days) if reminder.days else None,
        'active': reminder.active,
        'last_triggered': reminder.last_triggered.strftime('%Y-%m-%d %H:%M:%S') if reminder.last_triggered else None,
        'created_at': reminder.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/reminders/<int:reminder_id>', methods=['DELETE'])
@login_required
def delete_reminder(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    
    if reminder.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    db.session.delete(reminder)
    db.session.commit()
    
    return '', 204

@app.route('/api/reminders/check', methods=['GET'])
@login_required
def check_due_reminders():
    """Check for due reminders and return them"""
    now = datetime.now()
    current_time = now.time()
    current_weekday = now.strftime('%A').lower()
    
    # Get all active reminders for the user
    reminders = Reminder.query.filter_by(
        user_id=current_user.id,
        active=True
    ).all()
    
    due_reminders = []
    for reminder in reminders:
        # Check if reminder should trigger based on frequency
        should_trigger = False
        
        if reminder.frequency == 'daily':
            # For daily reminders, check if it's time
            should_trigger = (
                current_time.hour == reminder.time.hour and
                current_time.minute == reminder.time.minute and
                (not reminder.last_triggered or
                 reminder.last_triggered.date() < now.date())
            )
        
        elif reminder.frequency == 'weekly' and reminder.days:
            # For weekly reminders, check if it's the right day and time
            reminder_days = json.loads(reminder.days)
            if (current_weekday in reminder_days and
                current_time.hour == reminder.time.hour and
                current_time.minute == reminder.time.minute and
                (not reminder.last_triggered or
                 reminder.last_triggered.date() < now.date())):
                should_trigger = True
        
        if should_trigger:
            reminder.last_triggered = now
            db.session.commit()
            
            due_reminders.append({
                'id': reminder.id,
                'title': reminder.title,
                'description': reminder.description,
                'reminder_type': reminder.reminder_type,
                'time': reminder.time.strftime('%H:%M')
            })
    
    return jsonify(due_reminders)

@app.route('/api/statistics')
@login_required
def get_statistics():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Adjust end_date to include the entire day
    end_date = end_date.replace(hour=23, minute=59, second=59)
    
    print(f"Fetching statistics from {start_date} to {end_date}")  # Debug print
    
    # Get all records within date range
    exercises = Exercise.query.filter(
        Exercise.user_id == current_user.id,
        Exercise.date >= start_date,
        Exercise.date <= end_date
    ).order_by(Exercise.date).all()
    
    print(f"Found {len(exercises)} exercise records")  # Debug print
    for ex in exercises:
        print(f"Exercise: {ex.type} - {ex.duration} minutes on {ex.date}")  # Debug print
    
    # Exercise type distribution
    exercise_types = {
        'walking': 0,
        'running': 0,
        'cycling': 0,
        'swimming': 0,
        'gym': 0,
        'other': 0
    }
    
    # Calculate total duration for each exercise type
    for exercise in exercises:
        exercise_type = exercise.type.lower().strip()  # Convert to lowercase and remove whitespace
        if exercise_type in exercise_types:
            exercise_types[exercise_type] += exercise.duration
        else:
            exercise_types['other'] += exercise.duration
    
    print("Exercise type totals:", exercise_types)  # Debug print
    
    # Calculate daily exercise totals
    daily_exercise = {}
    for exercise in exercises:
        date_str = exercise.date.strftime('%Y-%m-%d')
        if date_str not in daily_exercise:
            daily_exercise[date_str] = 0
        daily_exercise[date_str] += exercise.duration
    
    # Get date range for the chart
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    # Fill in missing dates with 0
    exercise_values = [daily_exercise.get(date, 0) for date in date_range]
    
    # Calculate average exercise duration
    total_days = (end_date - start_date).days + 1
    avg_exercise = sum(daily_exercise.values()) / total_days if daily_exercise else 0
    
    # Calculate exercise trend
    exercise_trend = 0
    if daily_exercise:
        dates = sorted(daily_exercise.keys())
        if len(dates) > 1:
            first_val = daily_exercise[dates[0]]
            last_val = daily_exercise[dates[-1]]
            if first_val > 0:
                exercise_trend = ((last_val - first_val) / first_val) * 100
    
    # Get other data (weights, water, nutrition)
    weights = Weight.query.filter(
        Weight.user_id == current_user.id,
        Weight.date >= start_date,
        Weight.date <= end_date
    ).order_by(Weight.date).all()
    
    water_logs = WaterLog.query.filter(
        WaterLog.user_id == current_user.id,
        WaterLog.date >= start_date,
        WaterLog.date <= end_date
    ).order_by(WaterLog.date).all()
    
    nutrition_logs = NutritionLog.query.filter(
        NutritionLog.user_id == current_user.id,
        NutritionLog.date >= start_date,
        NutritionLog.date <= end_date
    ).order_by(NutritionLog.date).all()
    
    # Calculate daily averages for other metrics
    daily_calories = {}
    daily_water = {}
    
    for log in nutrition_logs:
        date_str = log.date.strftime('%Y-%m-%d')
        if date_str not in daily_calories:
            daily_calories[date_str] = 0
        daily_calories[date_str] += log.calories
    
    for log in water_logs:
        date_str = log.date.strftime('%Y-%m-%d')
        if date_str not in daily_water:
            daily_water[date_str] = 0
        daily_water[date_str] += log.amount
    
    avg_calories = sum(daily_calories.values()) / total_days if daily_calories else 0
    avg_water = sum(daily_water.values()) / total_days if daily_water else 0
    
    # Calculate weight change
    first_weight = weights[0].weight if weights else None
    last_weight = weights[-1].weight if weights else None
    
    # Calculate trends
    def calculate_trend(values):
        if not values:
            return 0
        dates = sorted(values.keys())
        if len(dates) < 2:
            return 0
        first_val = values[dates[0]]
        last_val = values[dates[-1]]
        if first_val == 0:
            return 0
        return ((last_val - first_val) / first_val) * 100
    
    # Calculate nutrition distribution
    total_protein = sum(log.protein for log in nutrition_logs if log.protein is not None)
    total_carbs = sum(log.carbs for log in nutrition_logs if log.carbs is not None)
    total_fat = sum(log.fat for log in nutrition_logs if log.fat is not None)
    
    return jsonify({
        'averages': {
            'calories': avg_calories,
            'water': avg_water,
            'exercise': avg_exercise
        },
        'weight': {
            'start': first_weight,
            'end': last_weight
        },
        'trends': {
            'calories': calculate_trend(daily_calories),
            'water': calculate_trend(daily_water),
            'exercise': exercise_trend,
            'weight': ((last_weight - first_weight) / first_weight * 100) if first_weight and last_weight else 0
        },
        'charts': {
            'weight': {
                'labels': [w.date.strftime('%Y-%m-%d') for w in weights],
                'values': [w.weight for w in weights]
            },
            'water': {
                'labels': date_range,
                'values': [daily_water.get(date, 0) for date in date_range]
            },
            'exercise': {
                'labels': date_range,
                'values': exercise_values
            },
            'nutrition': {
                'protein': total_protein,
                'carbs': total_carbs,
                'fat': total_fat
            },
            'exerciseTypes': exercise_types
        }
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 