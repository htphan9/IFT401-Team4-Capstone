from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from decimal import Decimal

app = Flask(__name__)
bcrypt = Bcrypt(app)
load_dotenv()

# Comment this out for local flask demo
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# # Configuration for Demo Only
# app.config['SQLALCHEMY_DATABASE_URI'] = \
#     'mysql+pymysql://root:password@localhost/capstone_db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SECRET_KEY'] = 'your-secret-key'

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
    user = db.relationship('Users', backref='audit_logs')
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
    user = db.relationship('Users', backref='transactions')
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    stock = db.relationship('Stock', backref='transactions')
    type = db.Column(db.String(20), nullable=False) # buy/sell
    amount = db.Column(db.Integer, nullable=False)
    price_at_execution = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(50), nullable=False)
    log_id = db.Column(db.Integer, db.ForeignKey('audit_log.id'))
    log = db.relationship('AuditLog', backref='transactions')
    market_id = db.Column(db.Integer, db.ForeignKey('market_configuration.id'))
    market = db.relationship('MarketConfiguration', backref='transactions')
 
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
    user = db.relationship('Users', backref='portfolios')
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    stock = db.relationship('Stock', backref='portfolios')
    cash_account_id = db.Column(db.Integer, db.ForeignKey('cash_account.id'), nullable=False)
    cash_account = db.relationship('CashAccount', backref='portfolios')
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
    account = CashAccount.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
    stocks = Stock.query.all()
    portfolio = Portfolio.query.filter(Portfolio.user_id == current_user.id, Portfolio.shares_owned > 0).all()

    return render_template("home.html", account=account, transactions=transactions, stocks=stocks, portfolio=portfolio)

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
    account = CashAccount.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
 
    return render_template("cash.html", account=account, transactions=transactions)

@app.route('/cash/deposit', methods=["POST"])
@login_required
def deposit():
    amount = Decimal(request.form.get("amount"))
 
    account = CashAccount.query.filter_by(user_id=current_user.id).first()
    if not account:
        # No account yet — create one with this deposit as the starting balance
        account = CashAccount(user_id=current_user.id, balance=amount)
        db.session.add(account)
    else:
        account.balance += amount
 
    # Log the deposit to the audit log
    log = AuditLog(
        user_id=current_user.id,
        activity_type="deposit",
        description=f"Deposited ${amount:.2f}"
    )
    db.session.add(log)
    db.session.commit()
 
    return redirect(url_for("cash"))
 
 
@app.route('/cash/withdraw', methods=["POST"])
@login_required
def withdraw():
    amount = Decimal(request.form.get("amount"))
 
    account = CashAccount.query.filter_by(user_id=current_user.id).first()
 
    # Block the withdrawal if the user doesn't have enough funds
    if not account or account.balance < amount:
        return render_template("cash.html", account=account, message="Insufficient funds.", message_type="danger")
 
    account.balance -= amount
 
    # Log the withdrawal to the audit log
    log = AuditLog(
        user_id=current_user.id,
        activity_type="withdrawal",
        description=f"Withdrew ${amount:.2f}"
    )
    db.session.add(log)
    db.session.commit()
 
    return redirect(url_for("cash"))

# History
@app.route('/history')
@login_required # Only logged-in users can access
def history():
    # Admins see everyone's data; regular users only see their own.
    # filter_by(user_id=...) scopes the query to the logged-in user.
    if current_user.role == "admin":
        transactions = Transaction.query.order_by(Transaction.id.desc()).all()
        audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    else:
        transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
        audit_logs = AuditLog.query.filter_by(user_id=current_user.id).order_by(AuditLog.timestamp.desc()).all()
 
    return render_template("history.html", transactions=transactions, audit_logs=audit_logs)

# Trading
@app.route('/trade', methods=['POST'])
@login_required
def trade():
    # Pull form data
    stock_id = request.form.get('stock_id', type=int)
    action = request.form.get('action')        # "buy" or "sell"
    quantity = request.form.get('quantity', type=int)

    # Basic validation
    if not stock_id or action not in ('buy', 'sell') or not quantity or quantity < 1:
        flash('Invalid trade request.', 'danger')
        return redirect(url_for('market'))

    # Load related records
    stock = Stock.query.get_or_404(stock_id)
    cash_account = CashAccount.query.filter_by(user_id=current_user.id).first()
    portfolio = Portfolio.query.filter_by(
        user_id=current_user.id,
        stock_id=stock_id
    ).first()

    price = stock.current_price
    total_cost = Decimal(quantity) * price

    # Buy
    if action == 'buy':

        # Check if market has enough shares
        if stock.available_inventory < quantity:
            flash(f'Not enough shares available. Only {stock.available_inventory} left.', 'danger')
            return redirect(url_for('market'))

        # Check the cash balance
        if cash_account.balance < total_cost:
            flash('Insufficient funds to complete this purchase.', 'danger')
            return redirect(url_for('market'))

        # Deduct cash from user
        cash_account.balance -= total_cost

        # Reduce market inventory
        stock.available_inventory -= quantity

        # Update daily high if new price qualifies
        if stock.daily_high is None or price > stock.daily_high:
            stock.daily_high = price

        # Add to portfolio (create row if first time buying this stock)
        if portfolio is None:
            portfolio = Portfolio(
                user_id=current_user.id,
                stock_id=stock_id,
                cash_account_id=cash_account.id,
                shares_owned=quantity
            )
            db.session.add(portfolio)
        else:
            portfolio.shares_owned += quantity

    # Sell
    elif action == 'sell':

        # Check if the user actually owns enough shares
        if portfolio is None or portfolio.shares_owned < quantity:
            owned = portfolio.shares_owned if portfolio else 0
            flash(f'You only own {owned} share(s) of {stock.ticker}.', 'danger')
            return redirect(url_for('home'))

        # Add cash back to user
        cash_account.balance += total_cost

        # Return shares to market inventory
        stock.available_inventory += quantity

        # Update daily low if new price qualifies
        if stock.daily_low is None or price < stock.daily_low:
            stock.daily_low = price

        # Reduce shares in portfolio
        portfolio.shares_owned -= quantity

    # Record in AuditLog
    audit = AuditLog(
        user_id=current_user.id,
        activity_type=action,
        description=f'{action.capitalize()} {quantity} share(s) of {stock.ticker} at ${price}'
    )
    db.session.add(audit)
    db.session.flush()  # get audit.id before committing

    # Record in Transaction
    transaction = Transaction(
        user_id=current_user.id,
        stock_id=stock_id,
        type=action,
        amount=quantity,
        price_at_execution=price,
        status='completed',
        log_id=audit.id
    )

    # Send and Save new transactions to the DB
    db.session.add(transaction)
    db.session.commit()

    flash(f'{action.capitalize()} {quantity} share(s) of {stock.ticker} completed!', 'success')
    # If action was buy, user was probably on market page. If sell, user was probably on portfolio page. 
    if action == 'sell':
        return redirect(url_for('home'))
    return redirect(url_for('market'))
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