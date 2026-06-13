from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Admin(db.Model, UserMixin):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(50), default='admin', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade="all, delete-orphan")
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True, cascade="all, delete-orphan")
    orders = db.relationship('Order', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    icon_path = db.Column(db.String(255), nullable=True)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)

    @property
    def url(self):
        if not self.image_path:
            return None
        path = self.image_path
        if path.startswith('http://') or path.startswith('https://'):
            return path
        if path.startswith('uploads/'):
            path = path[len('uploads/'):]
        from flask import url_for
        return url_for('uploaded_files', filename=path)

    @property
    def icon_url(self):
        if not self.icon_path:
            return self.url  # fallback to main image if icon doesn't exist
        path = self.icon_path
        if path.startswith('http://') or path.startswith('https://'):
            return path
        if path.startswith('uploads/'):
            path = path[len('uploads/'):]
        from flask import url_for
        return url_for('uploaded_files', filename=path)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    product_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_price = db.Column(db.Numeric(10, 2), nullable=True)
    description = db.Column(db.Text, nullable=True)
    material = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    availability_status = db.Column(db.String(50), default='In Stock', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    images = db.relationship('ProductImage', backref='product', lazy=True, cascade="all, delete-orphan")
    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade="all, delete-orphan")
    wishlist_items = db.relationship('WishlistItem', backref='product', lazy=True, cascade="all, delete-orphan")
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    reviews = db.relationship('Review', backref='product', lazy=True, cascade="all, delete-orphan")

    @property
    def get_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def primary_image(self):
        for img in self.images:
            if img.is_primary:
                return img.image_path
        if self.images:
            return self.images[0].image_path
        return 'images/placeholder.svg'

    @property
    def primary_image_url(self):
        img_path = self.primary_image
        if img_path.startswith('http://') or img_path.startswith('https://'):
            return img_path
        if img_path.startswith('uploads/'):
            img_path = img_path[len('uploads/'):]
        if img_path == 'images/placeholder.svg':
            from flask import url_for
            return url_for('static', filename='images/placeholder.svg')
        from flask import url_for
        return url_for('uploaded_files', filename=img_path)

class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    color = db.Column(db.String(50), nullable=True)

    @property
    def url(self):
        path = self.image_path
        if path.startswith('http://') or path.startswith('https://'):
            return path
        if path.startswith('uploads/'):
            path = path[len('uploads/'):]
        from flask import url_for
        return url_for('uploaded_files', filename=path)


class CartItem(db.Model):
    __tablename__ = 'cart'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WishlistItem(db.Model):
    __tablename__ = 'wishlists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    order_status = db.Column(db.String(50), default='Pending', nullable=False) # Pending, Paid, Processing, Shipped, Delivered, Cancelled, Payment Failed
    razorpay_order_id = db.Column(db.String(255), nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    courier_partner = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    payment = db.relationship('Payment', backref='order', uselist=False, cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False) # Captured price at checkout

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    transaction_id = db.Column(db.String(255), nullable=False) # razorpay_payment_id
    payment_method = db.Column(db.String(50), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False) # Captured, Failed, Refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Coupon(db.Model):
    __tablename__ = 'coupons'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), nullable=False) # percentage or flat
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    min_cart_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    
    def is_valid(self, cart_total):
        if not self.active:
            return False
        if datetime.utcnow().date() > self.expiry_date:
            return False
        if cart_total < self.min_cart_amount:
            return False
        return True

    def calculate_discount(self, cart_total):
        if not self.is_valid(cart_total):
            return 0.00
        if self.discount_type == 'percentage':
            return round((self.discount_value / 100) * cart_total, 2)
        elif self.discount_type == 'flat':
            return min(self.discount_value, cart_total)
        return 0.00

class Banner(db.Model):
    __tablename__ = 'banners'
    
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=True)
    subtitle = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    category = db.relationship('Category', backref='banners', lazy=True)

    @property
    def url(self):
        path = self.image_path
        if path.startswith('http://') or path.startswith('https://'):
            return path
        if path.startswith('uploads/'):
            path = path[len('uploads/'):]
        from flask import url_for
        return url_for('uploaded_files', filename=path)

