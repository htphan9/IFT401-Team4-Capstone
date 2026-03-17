from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
from dotenv import load_dotenv
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

# User model with role-based access control
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), default="user", nullable=False)

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
        hashed_password = bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8')

        is_admin = request.form.get("is_admin") == "on"
        role = "admin" if is_admin else "user"

        user = Users(
            username=request.form.get("username"),
            password=hashed_password,
            role=role
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

# Protected Home Route
@app.route('/')
@login_required # Only logged-in users can access
def home():
    return render_template("home.html")

@app.route('/market')
@login_required # Only logged-in users can access
def market():
    return render_template("market.html")

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

# Usage examples:
@app.route('/admin-dashboard')
@login_required
@admin_required
def admin_dashboard():
    users = Users.query.all()
    return render_template("admin_dashboard.html", users=users)

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