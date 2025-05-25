from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import json
import logging
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from utils import (
    create_item_directory, save_item_images, save_agreement_image,
    create_summary_file, init_db, save_to_db
)
from drive_utils import save_to_drive
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///business.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# Add custom filter for JSON
@app.template_filter('from_json')
def from_json(value):
    try:
        return json.loads(value)
    except:
        return {}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create instance folder if it doesn't exist
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)

# Initialize database on startup
def init_db():
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")

# Call init_db when the application starts
init_db()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)  # laptop or smartphone
    purchase_date = db.Column(db.Date, nullable=False)
    
    # Seller details
    seller_name = db.Column(db.String(100), nullable=False)
    seller_nic = db.Column(db.String(20), nullable=False)
    seller_contact = db.Column(db.String(20), nullable=False)
    seller_location = db.Column(db.String(200), nullable=False)
    
    # Buyer details
    buyer_name = db.Column(db.String(100))
    buyer_nic = db.Column(db.String(20))
    buyer_contact = db.Column(db.String(20))
    buyer_location = db.Column(db.String(200))
    
    # Specifications (stored as JSON)
    specifications = db.Column(db.Text, nullable=False)
    
    # Purchase details
    item_price = db.Column(db.Float, nullable=False)
    transport_cost = db.Column(db.Float, default=0)
    food_cost = db.Column(db.Float, default=0)
    fuel_cost = db.Column(db.Float, default=0)
    other_expenses = db.Column(db.Float, default=0)
    
    # File paths (stored as JSON)
    images = db.Column(db.Text, nullable=False)  # List of image paths
    agreement_image = db.Column(db.String(255), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Sale details (if sold)
    selling_date = db.Column(db.Date)
    selling_price = db.Column(db.Float)
    selling_expenses = db.Column(db.Float, default=0)
    gross_profit = db.Column(db.Float)
    net_profit = db.Column(db.Float)

    def __repr__(self):
        return f'<Item {self.name}>'

def save_image(file, item_id, image_type):
    if file and file.filename:
        filename = secure_filename(f"{item_id}_{image_type}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return filename
    return None

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
@login_required
def index():
    try:
        items = Item.query.order_by(Item.purchase_date.desc()).all()
        return render_template('index.html', items=items)
    except Exception as e:
        app.logger.error(f"Error loading items: {str(e)}")
        flash('Error loading items. Please try again.', 'error')
        return render_template('index.html', items=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))
            
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        try:
            # Log form data for debugging
            app.logger.debug("Form data received:")
            for key, value in request.form.items():
                app.logger.debug(f"{key}: {value}")

            # Get form data
            name = request.form['name']
            item_type = request.form['item_type']
            seller_name = request.form['seller_name']
            seller_nic = request.form['seller_nic']
            seller_contact = request.form['seller_contact']
            seller_location = request.form['seller_location']
            purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d')
            item_price = float(request.form['item_price'])
            remarks = request.form.get('remarks', '')  # Get remarks separately

            # Process expenses
            expenses = {
                'transport': float(request.form.get('expenses[transport]', 0)),
                'food': float(request.form.get('expenses[food]', 0)),
                'fuel': float(request.form.get('expenses[fuel]', 0)),
                'other': float(request.form.get('expenses[other]', 0))
            }

            # Process specifications based on item type
            app.logger.debug("Processing specifications with form data:")
            for key, value in request.form.items():
                app.logger.debug(f"{key}: {value}")

            if item_type == 'laptop':
                specs = {
                    'cpu': request.form['specs[cpu]'],
                    'cpu_speed': request.form['specs[cpu_speed]'],
                    'ram_capacity': request.form['specs[ram_capacity]'],
                    'ram_type': request.form['specs[ram_type]'],
                    'ram_speed': request.form['specs[ram_speed]'],
                    'storage_type': request.form['specs[storage_type]'],
                    'storage_size': request.form['specs[storage_size]'],
                    'gpu_type': request.form['specs[gpu_type]'],
                    'gpu_memory': request.form['specs[gpu_memory]'],
                    'display_type': request.form['specs[display_type]'],
                    'display_resolution': request.form['specs[display_resolution]'],
                    'features': request.form.getlist('specs[features][]')
                }
                if request.form['specs[display_resolution]'] == 'custom':
                    specs['display_resolution'] = request.form['specs[custom_resolution]']
            else:  # smartphone
                specs = {
                    'model': request.form['specs[model]'],
                    'capacity': request.form['specs[capacity]']
                }

            # Add remarks to specifications
            specs['remarks'] = remarks
            app.logger.debug(f"Final processed specifications: {specs}")

            # Create item directory structure
            item_dir = f"{name}_{purchase_date.strftime('%Y-%m-%d')}"
            product_images_dir = os.path.join(item_dir, 'Product images')
            agreement_dir = os.path.join(item_dir, 'Agreement')

            # Save item images
            item_images = request.files.getlist('item_images')
            image_paths = []
            for image in item_images:
                if image and image.filename:
                    # Save locally first
                    filename = secure_filename(image.filename)
                    local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(local_path)
                    
                    # Upload to Drive
                    drive_path = os.path.join(product_images_dir, filename)
                    web_link = save_to_drive(local_path, drive_path)
                    
                    # Clean up local file
                    os.remove(local_path)
                    
                    image_paths.append(web_link)

            # Save agreement image
            agreement_image = request.files['agreement_image']
            if agreement_image and agreement_image.filename:
                # Save locally first
                filename = secure_filename(agreement_image.filename)
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                agreement_image.save(local_path)
                
                # Upload to Drive
                drive_path = os.path.join(agreement_dir, filename)
                agreement_link = save_to_drive(local_path, drive_path)
                
                # Clean up local file
                os.remove(local_path)

            # Create new item
            new_item = Item(
                name=name,
                item_type=item_type,
                seller_name=seller_name,
                seller_nic=seller_nic,
                seller_contact=seller_contact,
                seller_location=seller_location,
                purchase_date=purchase_date,
                item_price=item_price,
                transport_cost=expenses['transport'],
                food_cost=expenses['food'],
                fuel_cost=expenses['fuel'],
                other_expenses=expenses['other'],
                specifications=json.dumps(specs),
                images=json.dumps(image_paths),
                agreement_image=agreement_link
            )

            db.session.add(new_item)
            db.session.commit()

            flash('Item added successfully!', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            app.logger.error(f"Error adding item: {str(e)}")
            flash(f'Error adding item: {str(e)}', 'error')
            return redirect(url_for('add_item'))

    return render_template('add_item.html')

@app.route('/check_db')
def check_db():
    try:
        # Check if tables exist using inspect
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        return f"Database tables: {tables}"
    except Exception as e:
        return f"Database error: {str(e)}"

@app.route('/mark_as_sold/<int:item_id>', methods=['POST'])
@login_required
def mark_as_sold(item_id):
    try:
        item = Item.query.get_or_404(item_id)
        
        # Log form data for debugging
        app.logger.debug("Form data received:")
        for key, value in request.form.items():
            app.logger.debug(f"{key}: {value}")
        
        # Process form data
        selling_date = datetime.strptime(request.form['selling_date'], '%Y-%m-%d').date()
        selling_price = float(request.form['selling_price'])
        transport_cost = float(request.form.get('transport_cost', 0))
        food_cost = float(request.form.get('food_cost', 0))
        fuel_cost = float(request.form.get('fuel_cost', 0))
        other_expenses = float(request.form.get('other_expenses', 0))
        
        # Calculate profits
        total_purchase_expenses = item.transport_cost + item.food_cost + item.fuel_cost + item.other_expenses
        total_sale_expenses = transport_cost + food_cost + fuel_cost + other_expenses
        
        # Gross profit is selling price minus purchase price
        gross_profit = selling_price - item.item_price
        
        # Net profit is gross profit minus all expenses (both purchase and sale expenses)
        net_profit = gross_profit - (total_purchase_expenses + total_sale_expenses)
        
        # Update item
        item.selling_date = selling_date
        item.selling_price = selling_price
        item.transport_cost = transport_cost
        item.food_cost = food_cost
        item.fuel_cost = fuel_cost
        item.other_expenses = other_expenses
        item.gross_profit = gross_profit
        item.net_profit = net_profit
        
        # Save buyer details
        item.buyer_name = request.form['buyer_name']
        item.buyer_contact = request.form['buyer_contact']
        item.buyer_location = request.form['buyer_location']
        item.buyer_nic = request.form.get('buyer_nic')
        
        # Log buyer details for debugging
        app.logger.debug("Buyer details being saved:")
        app.logger.debug(f"Name: {item.buyer_name}")
        app.logger.debug(f"Contact: {item.buyer_contact}")
        app.logger.debug(f"Location: {item.buyer_location}")
        app.logger.debug(f"NIC: {item.buyer_nic}")
        
        db.session.commit()
        flash('Item marked as sold successfully!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error marking item as sold: {str(e)}")
        flash('Error marking item as sold. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    try:
        item = Item.query.get_or_404(item_id)
        
        # Delete associated files
        try:
            # Delete item images
            for image_path in json.loads(item.images):
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            # Delete agreement image
            agreement_path = os.path.join(app.config['UPLOAD_FOLDER'], item.agreement_image)
            if os.path.exists(agreement_path):
                os.remove(agreement_path)
            
            # Delete the item's directory
            item_dir = os.path.dirname(agreement_path)
            if os.path.exists(item_dir):
                os.rmdir(item_dir)
        except Exception as e:
            app.logger.error(f"Error deleting files: {str(e)}")
        
        # Delete from database
        db.session.delete(item)
        db.session.commit()
        
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting item: {str(e)}")
        flash('Error deleting item. Please try again.', 'error')
    
    return redirect(url_for('index'))

@app.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    try:
        item = Item.query.get_or_404(item_id)
        
        if request.method == 'POST':
            # Get form data
            item.name = request.form['name']
            item.item_type = request.form['item_type']
            
            # Update seller details
            item.seller_name = request.form['seller_name']
            item.seller_nic = request.form['seller_nic']
            item.seller_contact = request.form['seller_contact']
            item.seller_location = request.form['seller_location']
            
            # Update purchase details
            item.purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d')
            item.item_price = float(request.form['item_price'])
            
            # Update purchase expenses
            item.transport_cost = float(request.form.get('transport_cost', 0))
            item.food_cost = float(request.form.get('food_cost', 0))
            item.fuel_cost = float(request.form.get('fuel_cost', 0))
            item.other_expenses = float(request.form.get('other_expenses', 0))
            
            # Process specifications
            if item.item_type == 'laptop':
                specs = {
                    'cpu': request.form['specs[cpu]'],
                    'cpu_speed': request.form['specs[cpu_speed]'],
                    'ram_capacity': request.form['specs[ram_capacity]'],
                    'ram_type': request.form['specs[ram_type]'],
                    'ram_speed': request.form['specs[ram_speed]'],
                    'storage_type': request.form['specs[storage_type]'],
                    'storage_size': request.form['specs[storage_size]'],
                    'gpu_type': request.form['specs[gpu_type]'],
                    'gpu_memory': request.form['specs[gpu_memory]'],
                    'display_type': request.form['specs[display_type]'],
                    'display_resolution': request.form['specs[display_resolution]'],
                    'features': request.form.getlist('specs[features][]'),
                    'remarks': request.form.get('specs[remarks]', '')
                }
            else:  # smartphone
                specs = {
                    'model': request.form['specs[model]'],
                    'capacity': request.form['specs[capacity]'],
                    'remarks': request.form.get('specs[remarks]', '')
                }
            item.specifications = json.dumps(specs)
            
            # Handle new images if uploaded
            if 'item_images' in request.files:
                new_images = request.files.getlist('item_images')
                if new_images and new_images[0].filename:
                    # Create new directory for this edit
                    item_dir = f"{item.name}_{item.purchase_date.strftime('%Y-%m-%d')}"
                    product_images_dir = os.path.join(item_dir, 'Product images')
                    
                    # Save new images
                    image_paths = []
                    for image in new_images:
                        if image and image.filename:
                            # Save locally first
                            filename = secure_filename(image.filename)
                            local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            image.save(local_path)
                            
                            # Upload to Drive
                            drive_path = os.path.join(product_images_dir, filename)
                            web_link = save_to_drive(local_path, drive_path)
                            
                            # Clean up local file
                            os.remove(local_path)
                            
                            image_paths.append(web_link)
                    
                    # Update images if new ones were uploaded
                    if image_paths:
                        item.images = json.dumps(image_paths)
            
            # Handle new agreement image if uploaded
            if 'agreement_image' in request.files:
                agreement_image = request.files['agreement_image']
                if agreement_image and agreement_image.filename:
                    # Create new directory for this edit
                    item_dir = f"{item.name}_{item.purchase_date.strftime('%Y-%m-%d')}"
                    agreement_dir = os.path.join(item_dir, 'Agreement')
                    
                    # Save locally first
                    filename = secure_filename(agreement_image.filename)
                    local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    agreement_image.save(local_path)
                    
                    # Upload to Drive
                    drive_path = os.path.join(agreement_dir, filename)
                    agreement_link = save_to_drive(local_path, drive_path)
                    
                    # Clean up local file
                    os.remove(local_path)
                    
                    item.agreement_image = agreement_link
            
            # If item is sold, update sale details
            if item.selling_price:
                item.selling_date = datetime.strptime(request.form['selling_date'], '%Y-%m-%d').date()
                item.selling_price = float(request.form['selling_price'])
                
                # Update sale expenses
                sale_transport_cost = float(request.form.get('sale_transport_cost', 0))
                sale_food_cost = float(request.form.get('sale_food_cost', 0))
                sale_fuel_cost = float(request.form.get('sale_fuel_cost', 0))
                sale_other_expenses = float(request.form.get('sale_other_expenses', 0))
                
                # Update buyer details
                item.buyer_name = request.form['buyer_name']
                item.buyer_contact = request.form['buyer_contact']
                item.buyer_location = request.form['buyer_location']
                item.buyer_nic = request.form.get('buyer_nic')
                
                # Recalculate profits
                total_purchase_expenses = item.transport_cost + item.food_cost + item.fuel_cost + item.other_expenses
                total_sale_expenses = sale_transport_cost + sale_food_cost + sale_fuel_cost + sale_other_expenses
                
                item.gross_profit = item.selling_price - item.item_price
                item.net_profit = item.gross_profit - (total_purchase_expenses + total_sale_expenses)
            
            db.session.commit()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('index'))
        
        # For GET request, prepare the data for the form
        specs = json.loads(item.specifications)
        return render_template('edit_item.html', item=item, specs=specs)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error editing item: {str(e)}")
        flash('Error editing item. Please try again.', 'error')
        return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(name=username).first()
        
        if user:
            # In a real application, you would:
            # 1. Generate a password reset token
            # 2. Send an email with a reset link
            # 3. Store the token in the database with an expiration time
            
            # For now, we'll just show a success message
            flash('If an account exists with that username, you will receive password reset instructions.', 'info')
        else:
            # Don't reveal whether the username exists or not
            flash('If an account exists with that username, you will receive password reset instructions.', 'info')
            
        return redirect(url_for('login'))
        
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    # In a real application, you would:
    # 1. Verify the token
    # 2. Check if it's expired
    # 3. Get the user associated with the token
    
    # For now, we'll just show a message
    flash('Password reset functionality is not implemented yet.', 'warning')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True) 