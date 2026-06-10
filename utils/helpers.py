import os
import re
from werkzeug.utils import secure_filename
from flask import current_app

def slugify(text):
    """
    Generate a clean, URL-friendly slug from string.
    """
    text = text.lower()
    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace multiple spaces/hyphens with a single hyphen
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')

def allowed_file(filename):
    """
    Check if the file has an allowed extension.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_product_image(file_storage, product_code, index):
    """
    Save an uploaded file into uploads/products/<product_code>/
    Returns the relative path to be saved in the database (e.g. 'uploads/products/PS1001/image1.jpg')
    """
    if not file_storage or file_storage.filename == '':
        return None
        
    if not allowed_file(file_storage.filename):
        return None

    # Target directory: uploads/products/<product_code>/
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products', product_code)
    os.makedirs(target_dir, exist_ok=True)
    
    # Get extension
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    
    # Standardized name: image<index>.<ext>
    safe_name = f"image{index}.{ext}"
    file_path = os.path.join(target_dir, safe_name)
    
    # Save the file
    file_storage.save(file_path)
    
    # Return path relative to the app context or web server
    # We will serve this folder via static routes
    return f"uploads/products/{product_code}/{safe_name}"

def save_banner_image(file_storage):
    """
    Save an uploaded banner file into uploads/banners/
    Returns the relative path to be saved in the database (e.g. 'banners/uuid.jpg')
    """
    import uuid
    if not file_storage or file_storage.filename == '':
        return None
        
    if not allowed_file(file_storage.filename):
        return None

    # Target directory: uploads/banners/
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'banners')
    os.makedirs(target_dir, exist_ok=True)
    
    # Get extension
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    
    # Standardized name
    safe_name = f"banner_{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(target_dir, safe_name)
    
    # Save the file
    file_storage.save(file_path)
    
    return f"banners/{safe_name}"
