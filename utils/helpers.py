import os
import re
from werkzeug.utils import secure_filename
from flask import current_app
import cloudinary
import cloudinary.uploader

def configure_cloudinary():
    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
        secure=True
    )

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
    Save an uploaded product image to Cloudinary (if credentials are set)
    or fall back to local storage.
    """
    if not file_storage or file_storage.filename == '':
        return None
        
    if not allowed_file(file_storage.filename):
        return None

    # If Cloudinary credentials are set, upload directly to the cloud
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
    
    if cloud_name and api_key and api_secret:
        try:
            configure_cloudinary()
            upload_result = cloudinary.uploader.upload(
                file_storage,
                folder=f"pstex/products/{product_code}",
                public_id=f"image{index}",
                overwrite=True
            )
            return upload_result.get("secure_url")
        except Exception as e:
            current_app.logger.warning(f"Cloudinary upload failed, falling back to local: {e}")

    # Fallback to local upload
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products', product_code)
    os.makedirs(target_dir, exist_ok=True)
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    safe_name = f"image{index}.{ext}"
    file_path = os.path.join(target_dir, safe_name)
    file_storage.save(file_path)
    return f"uploads/products/{product_code}/{safe_name}"

def save_banner_image(file_storage):
    """
    Save an uploaded banner file to Cloudinary or fall back to local.
    """
    import uuid
    if not file_storage or file_storage.filename == '':
        return None
        
    if not allowed_file(file_storage.filename):
        return None

    # If Cloudinary credentials are set, upload directly to the cloud
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
    
    if cloud_name and api_key and api_secret:
        try:
            configure_cloudinary()
            upload_result = cloudinary.uploader.upload(
                file_storage,
                folder="pstex/banners",
                public_id=f"banner_{uuid.uuid4().hex}"
            )
            return upload_result.get("secure_url")
        except Exception as e:
            current_app.logger.warning(f"Cloudinary banner upload failed, falling back to local: {e}")

    # Fallback to local upload
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'banners')
    os.makedirs(target_dir, exist_ok=True)
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    safe_name = f"banner_{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(target_dir, safe_name)
    file_storage.save(file_path)
    return f"banners/{safe_name}"
