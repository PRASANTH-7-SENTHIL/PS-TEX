import os
from flask import Flask, send_from_directory, session, redirect, url_for, flash
# pyrefly: ignore [missing-import]
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, Admin, User, Category, Coupon, Banner, Product, ProductImage

# Initialize extensions
csrf = CSRFProtect()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize plugins
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    # Session-based multi-user loader (Admin & User)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        if session.get('is_admin'):
            return Admin.query.get(int(user_id))
        return User.query.get(int(user_id))
        
    @login_manager.unauthorized_handler
    def unauthorized():
        if request_path_is_admin():
            flash('Please log in as an administrator.', 'danger')
            return redirect(url_for('admin.login'))
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth.login'))
        
    def request_path_is_admin():
        from flask import request
        return request.path.startswith('/admin')
    
    @app.route('/uploads/<path:filename>')
    def uploaded_files(filename):
        # If the filename is a full URL (e.g. from Cloudinary), redirect to it directly
        if filename.startswith('http://') or filename.startswith('https://'):
            return redirect(filename)
        # Handle cases where double slashes were merged by the router or client
        if filename.startswith('http:/') and not filename.startswith('http://'):
            return redirect(filename.replace('http:/', 'http://', 1))
        if filename.startswith('https:/') and not filename.startswith('https://'):
            return redirect(filename.replace('https:/', 'https://', 1))
            
        # Strip leading "uploads/" if present to prevent double nesting
        if filename.startswith('uploads/'):
            filename = filename[len('uploads/'):]
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

        
    # Inject cart count and categories into all templates
    @app.context_processor
    def inject_globals():
        from models import Category as Cat, CartItem
        # Check database connection exists
        try:
            cats = Cat.query.all()
        except Exception:
            cats = []
            
        cart_count = 0
        try:
            if current_user.is_authenticated and not session.get('is_admin'):
                cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
            elif 'cart' in session:
                cart_count = sum(session['cart'].values())
        except Exception:
            pass
            
        return dict(
            global_categories=cats,
            global_cart_count=cart_count,
            is_admin_session=session.get('is_admin', False)
        )
        
    # Register blueprints
    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.cart import cart_bp
    from routes.checkout import checkout_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(admin_bp)
    
    # Auto-create tables & seed data on startup
    with app.app_context():
        try:
            db.create_all()
            seed_database()
        except Exception as e:
            app.logger.warning(f"Database initialization skipped or failed: {str(e)}")
            
    return app

def seed_database():
    """
    Seeds database with default admin user, coupons, and basic categories if empty.
    """
    # 1. Seed admin
    admin_email = 'prasanth1619@gmail.com'
    existing_admin = Admin.query.filter_by(email=admin_email).first()
    if not existing_admin:
        admin = Admin(
            email=admin_email,
            name='Prasanth S',
            role='admin',
            phone='9876543210'
        )
        admin.set_password('@Prasanth1619')
        db.session.add(admin)
        print("Admin account seeded.")
    else:
        existing_admin.phone = '9876543210'
        
    # 2. Seed basic categories
    if Category.query.count() == 0:
        categories_to_seed = [
            {'name': 'Kanchipuram Silk Saree', 'slug': 'kanchipuram-silk', 'description': 'Lustrous, heavy silk sarees woven with pure gold zari borders from Tamil Nadu.', 'image_path': 'categories/kanchipuram.png'},
            {'name': 'Banarasi Silk Saree', 'slug': 'banarasi-silk', 'description': 'Opulent silk sarees featuring fine gold brocade embroidery from Varanasi.', 'image_path': 'categories/banarasi_saree.png', 'icon_path': 'categories/banarasi_saree_55.png'},
            {'name': 'Samuthrika Saree', 'slug': 'samuthrika-saree', 'description': 'Exquisite Samuthrika silk sarees featuring unique weaves, rich zari borders, and matching blouse pieces.', 'image_path': 'categories/samuthrika_saree.png', 'icon_path': 'categories/samuthrika_saree.png'},
            {'name': 'Cotton Saree', 'slug': 'cotton-saree', 'description': 'Breathable, handspun traditional daily-wear and office-wear cotton sarees.', 'image_path': 'categories/cotton_saree.png'}
        ]
        for cat_data in categories_to_seed:
            cat = Category(**cat_data)
            db.session.add(cat)
        print("Saree categories seeded.")
        
    # 3. Seed default coupon code
    if Coupon.query.count() == 0:
        from datetime import date
        coupon = Coupon(
            code='PSTEX10',
            discount_type='percentage',
            discount_value=10.00,
            min_cart_amount=1500.00,
            active=True,
            expiry_date=date(2028, 12, 31)
        )
        db.session.add(coupon)
        print("Default discount coupon seeded.")
        
    # 4. Remove default test Kanchipuram Silk Saree product if it exists
    existing_product = Product.query.filter_by(product_code='PS-TEST-KANCHI').first()
    if existing_product:
        db.session.delete(existing_product)
        print("Default test product removed.")
        
    db.session.commit()

app = create_app()

if __name__ == '__main__':
    # Create upload directories
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'products'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'banners'), exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
