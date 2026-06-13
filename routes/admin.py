import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Admin, User, Category, Product, ProductImage, Order, OrderItem, Payment, Banner
from utils.helpers import slugify, save_product_image, save_banner_image
from utils.security import validate_email, validate_password, validate_phone
import random
from datetime import datetime, timedelta
from sqlalchemy.sql import func

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def restrict_admin_routes():
    # Allow admin login page, password recovery, and static assets without session check
    exempt_endpoints = [
        'admin.login'
    ]
    if request.endpoint in exempt_endpoints:
        return
    # Check if user is logged in AND is verified as admin in session
    if not current_user.is_authenticated or not session.get('is_admin'):
        flash('Unauthorized. Please log in as Admin.', 'danger')
        return redirect(url_for('admin.login'))

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and session.get('is_admin'):
        return redirect(url_for('admin.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        admin = Admin.query.filter_by(email=email).first()
        if admin and admin.check_password(password):
            session['is_admin'] = True  # Set admin session flag
            login_user(admin)
            flash('Logged in to admin dashboard.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')
            
    return render_template('admin/login.html')

@admin_bp.route('/admin/logout')
def logout():
    logout_user()
    session.pop('is_admin', None)
    flash('Logged out from admin panel.', 'info')
    return redirect(url_for('admin.login'))

@admin_bp.route('/admin')
@admin_bp.route('/admin/dashboard')
def dashboard():
    # Metrics
    # Filter paid/shipped/delivered orders for revenue
    revenue_query = db.session.query(func.sum(Order.total_amount)).filter(
        Order.order_status.in_(['Paid', 'Processing', 'Shipped', 'Delivered'])
    ).scalar()
    total_revenue = float(revenue_query) if revenue_query else 0.0
    
    total_orders = Order.query.count()
    total_customers = User.query.count()
    out_of_stock_count = Product.query.filter(Product.stock_quantity == 0).count()
    
    # Recent 5 Orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Category Sales Summary
    category_data = db.session.query(
        Category.name, func.count(Product.id)
    ).join(Product, Category.id == Product.category_id).group_by(Category.name).all()
    
    return render_template('admin/dashboard.html', 
                           total_revenue=total_revenue, 
                           total_orders=total_orders, 
                           total_customers=total_customers, 
                           out_of_stock_count=out_of_stock_count,
                           recent_orders=recent_orders,
                           category_data=category_data)

# Category CRUD
@admin_bp.route('/admin/categories', methods=['GET', 'POST'])
def categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Category name is required.', 'danger')
        else:
            slug = slugify(name)
            existing = Category.query.filter((Category.name == name) | (Category.slug == slug)).first()
            if existing:
                flash('Category with this name or slug already exists.', 'danger')
            else:
                new_cat = Category(name=name, slug=slug, description=description)
                db.session.add(new_cat)
                db.session.commit()
                flash('Category added successfully.', 'success')
                return redirect(url_for('admin.categories'))
                
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/admin/categories/edit/<int:cat_id>', methods=['POST'])
def edit_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Category name cannot be empty.', 'danger')
    else:
        slug = slugify(name)
        existing = Category.query.filter(
            ((Category.name == name) | (Category.slug == slug)) & (Category.id != cat_id)
        ).first()
        if existing:
            flash('Category name already in use.', 'danger')
        else:
            category.name = name
            category.slug = slug
            category.description = description
            db.session.commit()
            flash('Category updated successfully.', 'success')
            
    return redirect(url_for('admin.categories'))

@admin_bp.route('/admin/categories/delete/<int:cat_id>', methods=['POST', 'GET'])
def delete_category(cat_id):
    category = Category.query.get_or_404(cat_id)
    # Check if products exist in category
    if category.products:
        flash('Cannot delete category. It contains active products. Reassign products first.', 'danger')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully.', 'success')
    return redirect(url_for('admin.categories'))

# Product CRUD
@admin_bp.route('/admin/products')
def products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@admin_bp.route('/admin/products/add', methods=['GET', 'POST'])
def add_product():
    categories = Category.query.all()
    if not categories:
        flash('Please create at least one category before adding products.', 'warning')
        return redirect(url_for('admin.categories'))
        
    if request.method == 'POST':
        product_code = request.form.get('product_code', '').strip().upper()
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        price = request.form.get('price', type=float)
        discount_price_raw = request.form.get('discount_price', '').strip()
        discount_price = float(discount_price_raw) if discount_price_raw else None
        description = request.form.get('description', '').strip()
        material = request.form.get('material', '').strip()
        color = request.form.get('color', '').strip()
        stock_quantity = request.form.get('stock_quantity', type=int, default=0)
        availability_status = request.form.get('availability_status', 'In Stock')
        
        if not product_code or not name or not category_id or price is None:
            flash('Product code, name, category, and price are required.', 'danger')
            return render_template('admin/products_form.html', categories=categories, action='Add')
            
        slug = slugify(name)
        # Verify unique constraints
        existing_code = Product.query.filter_by(product_code=product_code).first()
        existing_slug = Product.query.filter_by(slug=slug).first()
        
        if existing_code:
            flash(f'Product Code {product_code} is already assigned.', 'danger')
            return render_template('admin/products_form.html', categories=categories, action='Add')
        if existing_slug:
            slug = f"{slug}-{product_code.lower()}" # Fallback to prevent slug collision
            
        new_prod = Product(
            product_code=product_code,
            name=name,
            slug=slug,
            category_id=category_id,
            price=price,
            discount_price=discount_price,
            description=description,
            material=material,
            color=color,
            stock_quantity=stock_quantity,
            availability_status=availability_status
        )
        db.session.add(new_prod)
        db.session.flush() # Flush to get product.id for image references
        
        # Save multiple images
        # Save multiple images (from files or folder upload)
        images_list = request.files.getlist('images_folder')
        if not images_list or all(f.filename == '' for f in images_list):
            images_list = request.files.getlist('images')
            
        uploaded_files = [f for f in images_list if f and f.filename != '']
        image_colors = request.form.getlist('image_colors')
        
        saved_any = False
        img_index = 1
        
        for idx, file in enumerate(uploaded_files):
            saved_path = save_product_image(file, product_code, img_index)
            if saved_path:
                # Make the first successfully saved image the primary one
                is_primary = not saved_any
                color_val = image_colors[idx].strip() if idx < len(image_colors) else ''
                if not color_val:
                    color_val = None
                
                prod_img = ProductImage(
                    product_id=new_prod.id,
                    image_path=saved_path,
                    is_primary=is_primary,
                    color=color_val
                )
                db.session.add(prod_img)
                saved_any = True
                img_index += 1
                    
        try:
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
            
    return render_template('admin/products_form.html', categories=categories, action='Add', product=None)

@admin_bp.route('/admin/products/edit/<int:prod_id>', methods=['GET', 'POST'])
def edit_product(prod_id):
    product = Product.query.get_or_404(prod_id)
    categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        price = request.form.get('price', type=float)
        discount_price_raw = request.form.get('discount_price', '').strip()
        discount_price = float(discount_price_raw) if discount_price_raw else None
        description = request.form.get('description', '').strip()
        material = request.form.get('material', '').strip()
        color = request.form.get('color', '').strip()
        stock_quantity = request.form.get('stock_quantity', type=int, default=0)
        availability_status = request.form.get('availability_status', 'In Stock')
        
        if not name or not category_id or price is None:
            flash('Name, category, and price are required.', 'danger')
            return render_template('admin/products_form.html', categories=categories, action='Edit', product=product)
            
        slug = slugify(name)
        existing_slug = Product.query.filter((Product.slug == slug) & (Product.id != prod_id)).first()
        if existing_slug:
            slug = f"{slug}-{product.product_code.lower()}"
            
        product.name = name
        product.slug = slug
        product.category_id = category_id
        product.price = price
        product.discount_price = discount_price
        product.description = description
        product.material = material
        product.color = color
        product.stock_quantity = stock_quantity
        product.availability_status = availability_status if stock_quantity > 0 else 'Out of Stock'
        
        # Update existing images' colors
        for img in product.images:
            color_val = request.form.get(f'existing_image_color_{img.id}', '').strip()
            img.color = color_val if color_val else None

        # Save new images if uploaded
        images_list = request.files.getlist('images_folder')
        if not images_list or all(f.filename == '' for f in images_list):
            images_list = request.files.getlist('images')
            
        uploaded_files = [f for f in images_list if f and f.filename != '']
        image_colors = request.form.getlist('image_colors')
        
        # Determine current index
        current_img_count = len(product.images)
        img_index = current_img_count + 1
        
        # Check if product has primary image
        has_primary = any([img.is_primary for img in product.images])
        
        for idx, file in enumerate(uploaded_files):
            saved_path = save_product_image(file, product.product_code, img_index)
            if saved_path:
                is_primary = not has_primary
                color_val = image_colors[idx].strip() if idx < len(image_colors) else ''
                if not color_val:
                    color_val = None
                
                prod_img = ProductImage(
                    product_id=product.id,
                    image_path=saved_path,
                    is_primary=is_primary,
                    color=color_val
                )
                db.session.add(prod_img)
                has_primary = True
                img_index += 1
                    
        try:
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
            
    return render_template('admin/products_form.html', categories=categories, action='Edit', product=product)

@admin_bp.route('/admin/products/delete/<int:prod_id>', methods=['POST', 'GET'])
def delete_product(prod_id):
    product = Product.query.get_or_404(prod_id)
    # Remove files under product code folder
    prod_code = product.product_code
    try:
        # Delete DB entries first (cascade deletes images in database)
        db.session.delete(product)
        db.session.commit()
        
        # Attempt to delete local directory
        target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products', prod_code)
        if os.path.exists(target_dir):
            for file in os.listdir(target_dir):
                os.remove(os.path.join(target_dir, file))
            os.rmdir(target_dir)
            
        flash('Product and associated images deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Product deleted from database, but image folder cleanup failed: {str(e)}', 'warning')
        
    return redirect(url_for('admin.products'))

@admin_bp.route('/admin/products/delete-image/<int:img_id>', methods=['POST'])
def delete_product_image(img_id):
    img = ProductImage.query.get_or_404(img_id)
    product = img.product
    
    # Prevent deleting primary image if it's the only one
    if img.is_primary and len(product.images) > 1:
        # Reassign primary to another image
        next_img = [i for i in product.images if i.id != img_id][0]
        next_img.is_primary = True
        
    try:
        # Delete local file
        local_path = os.path.join(current_app.config['BASE_DIR'], img.image_path)
        if os.path.exists(local_path):
            os.remove(local_path)
            
        db.session.delete(img)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Image deleted successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/admin/products/set-primary-image/<int:img_id>', methods=['POST'])
def set_primary_image(img_id):
    img = ProductImage.query.get_or_404(img_id)
    product = img.product
    
    # Set all other product images to is_primary = False
    for other_img in product.images:
        other_img.is_primary = (other_img.id == img_id)
        
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Primary image updated.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Orders management
@admin_bp.route('/admin/orders')
def orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@admin_bp.route('/admin/orders/details/<int:order_id>')
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_details.html', order=order)

@admin_bp.route('/admin/orders/update-status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get('status')
    tracking_number = request.form.get('tracking_number', '').strip()
    courier_partner = request.form.get('courier_partner', '').strip()
    
    if status not in ['Pending', 'Paid', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
        flash('Invalid status code.', 'danger')
        return redirect(url_for('admin.order_details', order_id=order_id))
        
    order.order_status = status
    if tracking_number:
        order.tracking_number = tracking_number
    if courier_partner:
        order.courier_partner = courier_partner
        
    db.session.commit()
    flash(f'Order {order.order_number} status updated to {status}.', 'success')
    return redirect(url_for('admin.order_details', order_id=order_id))

# Customers List
@admin_bp.route('/admin/customers')
def customers():
    customers = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/customers.html', customers=customers)

# Revenue Reports
@admin_bp.route('/admin/reports')
def reports():
    start_date_raw = request.args.get('start_date')
    end_date_raw = request.args.get('end_date')
    
    # Default to last 30 days
    if start_date_raw:
        start_date = datetime.strptime(start_date_raw, '%Y-%m-%d')
    else:
        start_date = datetime.utcnow() - timedelta(days=30)
        start_date_raw = start_date.strftime('%Y-%m-%d')
        
    if end_date_raw:
        end_date = datetime.strptime(end_date_raw, '%Y-%m-%d') + timedelta(days=1)
    else:
        end_date = datetime.utcnow() + timedelta(days=1)
        end_date_raw = (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
        
    orders = Order.query.filter(
        Order.created_at >= start_date,
        Order.created_at < end_date,
        Order.order_status.in_(['Paid', 'Processing', 'Shipped', 'Delivered'])
    ).order_by(Order.created_at.desc()).all()
    
    total_sales = sum([float(o.total_amount) for o in orders])
    total_orders = len(orders)
    
    return render_template('admin/reports.html', 
                           orders=orders, 
                           total_sales=total_sales, 
                           total_orders=total_orders,
                           start_date=start_date_raw,
                           end_date=end_date_raw)

# Settings (Modify admin profile & password credentials)
@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    admin = Admin.query.get(current_user.id)
    categories = Category.query.all()
    banners = Banner.query.order_by(Banner.created_at.asc()).all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'upload_banner':
            title = request.form.get('title', '').strip()
            subtitle = request.form.get('subtitle', '').strip()
            category_id_raw = request.form.get('category_id')
            category_id = int(category_id_raw) if category_id_raw and category_id_raw.isdigit() else None
            
            file = request.files.get('banner_image')
            if file and file.filename != '':
                saved_path = save_banner_image(file)
                if saved_path:
                    new_banner = Banner(
                        image_path=saved_path,
                        title=title if title else None,
                        subtitle=subtitle if subtitle else None,
                        category_id=category_id
                    )
                    db.session.add(new_banner)
                    db.session.commit()
                    flash('Banner uploaded successfully!', 'success')
                else:
                    flash('Invalid banner file format. Allowed types: png, jpg, jpeg, webp.', 'danger')
            else:
                flash('Please select an image file to upload.', 'danger')
            return redirect(url_for('admin.settings'))
            
        else:
            # Handle Change Credentials
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not name or not email:
                flash('Name and email are required.', 'danger')
                return render_template('admin/settings.html', admin=admin, categories=categories, banners=banners)
                
            if not validate_email(email):
                flash('Invalid email format.', 'danger')
                return render_template('admin/settings.html', admin=admin, categories=categories, banners=banners)
                
            existing = Admin.query.filter((Admin.email == email) & (Admin.id != admin.id)).first()
            if existing:
                flash('Email address already in use.', 'danger')
                return render_template('admin/settings.html', admin=admin, categories=categories, banners=banners)
                
            admin.name = name
            admin.email = email
            
            if old_password or new_password or confirm_password:
                if not admin.check_password(old_password):
                    flash('Incorrect current password.', 'danger')
                    return render_template('admin/settings.html', admin=admin, categories=categories, banners=banners)
                    
                if not validate_password(new_password):
                    flash('New password does not meet requirements.', 'danger')
                    return render_template('admin/settings.html', admin=admin, categories=categories, banners=banners)
                    
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    return render_template('admin/settings.html', admin=admin, categories=categories, banners=banners)
                    
                admin.set_password(new_password)
                
            try:
                db.session.commit()
                flash('Admin settings updated successfully.', 'success')
            except Exception:
                db.session.rollback()
                flash('Error saving changes.', 'danger')
                
            return redirect(url_for('admin.settings'))
            
    return render_template('admin/settings.html', admin=admin, categories=categories, banners=banners)

@admin_bp.route('/admin/settings/banners/delete/<int:banner_id>', methods=['POST'])
def delete_banner(banner_id):
    banner = Banner.query.get_or_404(banner_id)
    try:
        # Delete local file from disk
        local_path = os.path.join(current_app.config['UPLOAD_FOLDER'], banner.image_path)
        if os.path.exists(local_path):
            os.remove(local_path)
        db.session.delete(banner)
        db.session.commit()
        flash('Banner deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting banner: {str(e)}', 'danger')
    return redirect(url_for('admin.settings'))



