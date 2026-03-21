from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
import os

app = Flask(__name__)
bcrypt = Bcrypt(app)
load_dotenv()

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# https://www.learnbyexample.org/working-with-timezones-in-python/
# Convert UTC to America/Phoenix
def az_time():
    return datetime.now(ZoneInfo("America/Phoenix"))

# User model with role-based access control
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(39), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="user", nullable=False)

# Cash model
class CashAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    balance = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    ticker = db.Column(db.String(10), nullable=False)
    total_shares_issued = db.Column(db.Integer, nullable=False)
    available_inventory = db.Column(db.Integer, nullable=False)
    current_price = db.Column(db.Numeric(10, 2), nullable=False)
    opening_price = db.Column(db.Numeric(10, 2), nullable=False)
    daily_high = db.Column(db.Numeric(10, 2))
    daily_low = db.Column(db.Numeric(10, 2))
    initial_price = db.Column(db.Numeric(10, 2), nullable=False)

# Audit model
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, nullable=False, default=az_time)

# Market model
class MarketConfiguration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    market_hours = db.Column(db.String(100), nullable=False)
    market_schedule = db.Column(db.String(100), nullable=False)

# Transactions model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False) # buy/sell
    amount = db.Column(db.Integer, nullable=False)
    price_at_execution = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(50), nullable=False)
    log_id = db.Column(db.Integer, db.ForeignKey('audit_log.id'))
    market_id = db.Column(db.Integer, db.ForeignKey('market_configuration.id'))
 
# Holiday model
class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey('market_configuration.id'), nullable=False)
    holiday_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255))

# Portfolio model
class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    cash_account_id = db.Column(db.Integer, db.ForeignKey('cash_account.id'), nullable=False)
    shares_owned = db.Column(db.Integer, nullable=False, default=0)

# Initialize database
with app.app_context():
    db.create_all()

# User loader - required by Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

# Registration Route
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
 
        if password != confirm_password:
            return render_template("sign_up.html", error="Passwords do not match.")

        hashed_password = bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8')

        user = Users(
            full_name=request.form.get("full_name"),
            username=request.form.get("username"),
            password=hashed_password,
            email=request.form.get("email"),
            role="user"
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    
    return render_template("sign_up.html")

# Login Route
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = Users.query.filter_by(
            username=request.form.get("username")
        ).first()
        
        if user and bcrypt.check_password_hash(
            user.password, request.form.get("password")
        ): 
            login_user(user)
            return redirect(url_for("home"))

    return render_template("login.html")

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# Custom Decorators for Role Checking
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

# More flexible version for multiple roles:
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Protected Home Route
@app.route('/')
@login_required # Only logged-in users can access
def home():
    return render_template("home.html")

# Market
@app.route('/market')
@login_required # Only logged-in users can access
def market():
    stocks = Stock.query.all()
    return render_template("market.html", stocks=stocks)

# Cash
@app.route('/cash')
@login_required # Only logged-in users can access
def cash():
    return render_template("cash.html")

# History
@app.route('/history')
@login_required # Only logged-in users can access
def history():
    # Admins see everyone's data; regular users only see their own.
    # filter_by(user_id=...) scopes the query to the logged-in user.
    if current_user.role == "admin":
        transactions = Transaction.query.all()
        audit_logs = AuditLog.query.all()
    else:
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        audit_logs = AuditLog.query.filter_by(user_id=current_user.id).all()
 
    return render_template("history.html", transactions=transactions, audit_logs=audit_logs)

# Admin
@app.route('/admin')
@login_required # Only logged-in users can access
@admin_required # Only Admins can access
def admin():
    return render_template("admin.html")

# Usage examples:
# @app.route('/admin')
# @login_required
# @admin_required
# def admin_dashboard():
#     users = Users.query.all()
#     return render_template("admin.html", users=users)

# 6. (Optional) Creating an Admin User
# with app.app_context():
#     admin = Users(
#         username="admin",
#         password=bcrypt.generate_password_hash("admin123").decode('utf-8'),
#         role="admin"
#     )
#     db.session.add(admin)
#     db.session.commit()
#     print("Admin user created!")