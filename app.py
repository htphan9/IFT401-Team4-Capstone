from flask import Flask, render_template, request, url_for, redirect, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime, date
from zoneinfo import ZoneInfo
import os
from decimal import Decimal
import threading
import time
import random

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
    open_time = db.Column(db.String(5), nullable=False, default='09:30')
    close_time = db.Column(db.String(5), nullable=False, default='16:00')

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

# Check if the market is currently open
def is_market_open():
    now = az_time()

    # Market is closed on weekends (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        return False

    # Check if today is a holiday
    today = now.date()
    holiday = Holiday.query.filter_by(holiday_date=today).first()
    if holiday:
        return False

    # Check market hours from the database
    config = MarketConfiguration.query.first()
    if not config:
        return False

    open_parts = config.open_time.split(':')
    close_parts = config.close_time.split(':')
    open_time = now.replace(hour=int(open_parts[0]), minute=int(open_parts[1]), second=0)
    close_time = now.replace(hour=int(close_parts[0]), minute=int(close_parts[1]), second=0)

    return open_time <= now <= close_time

# Get a user's portfolio holdings with average cost per stock
def get_user_holdings(user_id):
    positions = Portfolio.query.filter(
        Portfolio.user_id == user_id,
        Portfolio.shares_owned > 0
    ).all()

    holdings = {}
    for pos in positions:
        buy_txns = Transaction.query.filter_by(
            user_id=user_id, stock_id=pos.stock_id, type='buy'
        ).order_by(Transaction.id.desc()).all()

        shares_to_account = pos.shares_owned
        total_cost = Decimal('0')
        for txn in buy_txns:
            if shares_to_account <= 0:
                break
            applicable = min(txn.amount, shares_to_account)
            total_cost += Decimal(str(txn.price_at_execution)) * applicable
            shares_to_account -= applicable

        if pos.shares_owned > 0:
            avg_cost = total_cost / pos.shares_owned
        else:
            avg_cost = Decimal('0')

        holdings[pos.stock_id] = {
            'position': pos,
            'shares_owned': pos.shares_owned,
            'avg_cost': avg_cost,
            'total_cost': total_cost
        }

    return holdings


# Update stock prices every 5 minutes
def update_prices(app):
    while True:
        time.sleep(300) # 300 for 5 minutes
        with app.app_context():
            # Skip price updates when the market is closed
            if not is_market_open():
                continue

            stocks = Stock.query.all()
            for stock in stocks:
                change = random.uniform(-0.05, 0.05)
                new_price = stock.current_price * Decimal(str(1 + change))
                new_price = round(new_price, 2)

                # Keep price from going below $1
                if new_price < Decimal('1.00'):
                    new_price = Decimal('1.00')

                stock.current_price = new_price

                # Update daily high and low
                if stock.daily_high is None or new_price > stock.daily_high:
                    stock.daily_high = new_price
                if stock.daily_low is None or new_price < stock.daily_low:
                    stock.daily_low = new_price

            db.session.commit()

# Initialize database
with app.app_context():
    db.create_all()

    # Hardcode 2026 US stock market holidays
    # Only inserts if the holiday table is empty — prevents duplicates on restart
    if Holiday.query.count() == 0:

        # Get the market config id (holidays need a market_id foreign key)
        config = MarketConfiguration.query.first()

        if config:
            holidays_2026 = [
                (date(2026, 1,  1),  "New Year's Day"),
                (date(2026, 1, 19),  "Martin Luther King Jr. Day"),
                (date(2026, 2, 16),  "Presidents' Day"),
                (date(2026, 4, 18),  "Good Friday"),
                (date(2026, 5, 25),  "Memorial Day"),
                (date(2026, 7,  3),  "Independence Day (observed)"),
                (date(2026, 9,  7),  "Labor Day"),
                (date(2026, 11, 26), "Thanksgiving Day"),
                (date(2026, 12, 25), "Christmas Day"),
            ]

            for holiday_date, description in holidays_2026:
                holiday = Holiday(
                    market_id=config.id,
                    holiday_date=holiday_date,
                    description=description
                )
                db.session.add(holiday)

            db.session.commit()

# Start background thread for price updates
thread = threading.Thread(target=update_prices, args=(app,), daemon=True)
thread.start()

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

# API endpoint for getting current stock prices
@app.route('/api/prices')
@login_required
def api_prices():
    stocks = Stock.query.all()
    data = {}
    for stock in stocks:
        data[str(stock.id)] = {
            'price': float(stock.current_price),
            'high': float(stock.daily_high) if stock.daily_high else None,
            'low': float(stock.daily_low) if stock.daily_low else None,
            'available': stock.available_inventory
        }
    return jsonify(data)

# Protected Home Route
@app.route('/')
@login_required
def home():
    account = CashAccount.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
    stocks = Stock.query.all()
    holdings = get_user_holdings(current_user.id)

    portfolio = []
    for stock_id, data in holdings.items():
        pos = data['position']
        avg_cost = data['avg_cost']
        total_cost = data['total_cost']

        buy_txns = Transaction.query.filter_by(
            user_id=current_user.id, stock_id=stock_id, type='buy'
        ).order_by(Transaction.id.desc()).all()

        market_value = Decimal(str(pos.stock.current_price)) * pos.shares_owned
        pos.avg_cost = avg_cost
        pos.price_at_execution = Decimal(str(buy_txns[0].price_at_execution)) if buy_txns else Decimal('0')
        pos.unrealized_pnl = market_value - total_cost
        portfolio.append(pos)

    return render_template("home.html", account=account, transactions=transactions, stocks=stocks, portfolio=portfolio, is_open=is_market_open())

# Market
@app.route('/market')
@login_required # Only logged-in users can access
def market():
    stocks = Stock.query.all()
    account = CashAccount.query.filter_by(user_id=current_user.id).first()
    holdings = get_user_holdings(current_user.id)

    # Convert to a simpler dict for the template
    user_holdings = {}
    for stock_id, data in holdings.items():
        user_holdings[stock_id] = {
            'shares_owned': data['shares_owned'],
            'avg_cost': round(float(data['avg_cost']), 2)
        }

    return render_template("market.html", stocks=stocks, is_open=is_market_open(), account=account, user_holdings=user_holdings)    
# Cash
@app.route('/cash')
@login_required # Only logged-in users can access
def cash():
    account = CashAccount.query.filter_by(user_id=current_user.id).first()
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.id.desc()).all()
 
    return render_template("cash.html", account=account, transactions=transactions, is_open=is_market_open())

@app.route('/cash/deposit', methods=["POST"])
@login_required
def deposit():
    amount = Decimal(request.form.get("amount"))
    MAX_BALANCE = Decimal('9999999999.99')
 
    account = CashAccount.query.filter_by(user_id=current_user.id).first()

    if amount > MAX_BALANCE or (account and account.balance + amount > MAX_BALANCE):
        flash("Transaction exceeds maximum account balance limit.", "danger")
        return redirect(url_for("cash"))

    if not account:
        # No account yet — create one with this deposit as the starting balance
        account = CashAccount(user_id=current_user.id, balance=amount)
        db.session.add(account)
    else:
        account.balance += amount
    
    flash(f'Deposit of ${amount:.2f} successful.', 'success') 

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
        flash("Insufficient funds.", "danger")
        return redirect(url_for("cash"))
         
    account.balance -= amount
 
    flash(f'Withdrawal of ${amount:.2f} successful.', 'success')

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
 
    return render_template("history.html", transactions=transactions, audit_logs=audit_logs, is_open=is_market_open())

# Trading
@app.route('/trade', methods=['POST'])
@login_required
def trade():
    # Block trades when the market is closed
    if not is_market_open():
        flash('The market is currently closed. Trades cannot be executed.', 'danger')
        return redirect(url_for('market'))

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
    stocks = Stock.query.all()
    market_config = MarketConfiguration.query.first()
    holidays = Holiday.query.order_by(Holiday.holiday_date).all()
    return render_template("admin.html", stocks=stocks, market_config=market_config, holidays=holidays, is_open=is_market_open())

# Update market hours
@app.route('/admin/update_market', methods=['POST'])
@login_required
@admin_required
def update_market():
    open_time = request.form.get('open_time')
    close_time = request.form.get('close_time')

    config = MarketConfiguration.query.first()
    if not config:
        config = MarketConfiguration(open_time=open_time, close_time=close_time)
        db.session.add(config)
    else:
        config.open_time = open_time
        config.close_time = close_time

    db.session.commit()
    flash('Market hours updated.', 'success')
    return redirect(url_for('admin'))

# Add a new stock
@app.route('/admin/add_stock', methods=['POST'])
@login_required
@admin_required
def add_stock():
    # Pull values from the admin form
    ticker       = request.form.get('ticker').strip().upper()
    company_name = request.form.get('company_name').strip()
    initial_price  = Decimal(request.form.get('initial_price'))
    initial_volume = int(request.form.get('initial_volume_issued'))

    # Check if a stock with this ticker already exists
    existing = Stock.query.filter_by(ticker=ticker).first()
    if existing:
        flash(f'A stock with ticker {ticker} already exists.', 'danger')
        return redirect(url_for('admin'))

    # Create the new stock row
    stock = Stock(
        ticker=ticker,
        company_name=company_name,
        initial_price=initial_price,
        current_price=initial_price,
        opening_price=initial_price,
        total_shares_issued=initial_volume,
        available_inventory=initial_volume,
        daily_high=None,
        daily_low=None
    )
    db.session.add(stock)

    # Log the action to the audit log
    audit = AuditLog(
        user_id=current_user.id,
        activity_type='add_stock',
        description=f'Added stock {ticker} ({company_name}) at ${initial_price}'
    )
    db.session.add(audit)
    db.session.commit()

    flash(f'{ticker} added successfully.', 'success')
    return redirect(url_for('admin'))

# Delete a stock
@app.route('/admin/delete_stock', methods=['POST'])
@login_required
@admin_required
def delete_stock():
    stock_id = request.form.get('stock_id', type=int)

    # Load the stock
    stock = Stock.query.get_or_404(stock_id)

    # Block the delete if any transactions reference this stock
    existing_transactions = Transaction.query.filter_by(stock_id=stock_id).first()
    if existing_transactions:
        flash(f'Cannot delete {stock.ticker} — it has existing transactions.', 'danger')
        return redirect(url_for('admin'))

    # Safe to delete/clean up any lingering portfolio rows first
    Portfolio.query.filter_by(stock_id=stock_id).delete()

    # Delete the stock itself
    db.session.delete(stock)

    # Log the action
    audit = AuditLog(
        user_id=current_user.id,
        activity_type='delete_stock',
        description=f'Deleted stock {stock.ticker} ({stock.company_name})'
    )
    db.session.add(audit)

    # Commit everything at once
    db.session.commit()

    flash(f'{stock.ticker} deleted successfully.', 'success')
    return redirect(url_for('admin'))

# Add a holiday
@app.route('/admin/add_holiday', methods=['POST'])
@login_required
@admin_required
def add_holiday():
    holiday_date = request.form.get('holiday_date')  # comes in as a string "YYYY-MM-DD"
    description  = request.form.get('description')

    config = MarketConfiguration.query.first()
    if not config:
        flash('Set market hours before adding holidays.', 'danger')
        return redirect(url_for('admin'))

    # Option A — check if this date already exists before inserting
    from datetime import date
    parsed_date = date.fromisoformat(holiday_date)
    exists = Holiday.query.filter_by(holiday_date=parsed_date).first()
    if exists:
        flash(f'{holiday_date} is already a holiday.', 'danger')
        return redirect(url_for('admin'))

    holiday = Holiday(
        market_id=config.id,
        holiday_date=parsed_date,
        description=description
    )
    db.session.add(holiday)
    db.session.commit()

    flash(f'Holiday added: {description or holiday_date}.', 'success')
    return redirect(url_for('admin'))