import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import sqlite3

def create_item_directory(item_name):
    """Create directory structure for item files"""
    # Create base directory with item name and date
    base_dir = os.path.join(os.getcwd(), 'items', f"{item_name}_{datetime.now().strftime('%Y%m%d')}")
    os.makedirs(base_dir, exist_ok=True)
    
    # Create subdirectories
    images_dir = os.path.join(base_dir, 'Images')
    agreement_dir = os.path.join(base_dir, 'Agreement')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(agreement_dir, exist_ok=True)
    
    return base_dir, images_dir, agreement_dir

def save_item_images(images, images_dir):
    """Save multiple item images"""
    saved_paths = []
    for image in images:
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(images_dir, filename)
            image.save(filepath)
            saved_paths.append(filepath)
    return saved_paths

def save_agreement_image(agreement_image, agreement_dir):
    """Save agreement image"""
    if agreement_image:
        filename = secure_filename(agreement_image.filename)
        filepath = os.path.join(agreement_dir, filename)
        agreement_image.save(filepath)
        return filepath
    return None

def create_summary_file(base_dir, form_data):
    """Create a text file with form summary"""
    summary_path = os.path.join(base_dir, 'summary.txt')
    with open(summary_path, 'w') as f:
        f.write("Purchase Summary\n")
        f.write("===============\n\n")
        f.write(f"Date: {form_data.get('purchase_date')}\n")
        f.write(f"Item Name: {form_data.get('name')}\n")
        f.write(f"Item Type: {form_data.get('item_type')}\n\n")
        
        f.write("Seller Details\n")
        f.write("-------------\n")
        f.write(f"Name: {form_data.get('seller_name')}\n")
        f.write(f"NIC: {form_data.get('seller_nic')}\n")
        f.write(f"Contact: {form_data.get('seller_contact')}\n")
        f.write(f"Location: {form_data.get('seller_location')}\n\n")
        
        f.write("Specifications\n")
        f.write("-------------\n")
        for key, value in form_data.get('specs', {}).items():
            f.write(f"{key}: {value}\n")
        
        f.write("\nPurchase Details\n")
        f.write("---------------\n")
        f.write(f"Item Price: Rs. {form_data.get('item_price')}\n")
        for expense_type, amount in form_data.get('expenses', {}).items():
            f.write(f"{expense_type.title()}: Rs. {amount}\n")

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('gse.db')
    c = conn.cursor()
    
    # Create items table
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            purchase_date DATE NOT NULL,
            seller_name TEXT NOT NULL,
            seller_nic TEXT NOT NULL,
            seller_contact TEXT NOT NULL,
            seller_location TEXT NOT NULL,
            specs TEXT NOT NULL,
            item_price REAL NOT NULL,
            expenses TEXT NOT NULL,
            images TEXT NOT NULL,
            agreement_image TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_to_db(form_data, images_paths, agreement_path):
    """Save item data to SQLite database"""
    conn = sqlite3.connect('gse.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO items (
            name, item_type, purchase_date, seller_name, seller_nic,
            seller_contact, seller_location, specs, item_price,
            expenses, images, agreement_image
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        form_data['name'],
        form_data['item_type'],
        form_data['purchase_date'],
        form_data['seller_name'],
        form_data['seller_nic'],
        form_data['seller_contact'],
        form_data['seller_location'],
        json.dumps(form_data['specs']),
        form_data['item_price'],
        json.dumps(form_data['expenses']),
        json.dumps(images_paths),
        agreement_path
    ))
    
    conn.commit()
    conn.close() 