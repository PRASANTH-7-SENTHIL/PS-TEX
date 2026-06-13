from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import current_user, login_required
from models import db, Product, CartItem, WishlistItem

cart_bp = Blueprint('cart', __name__)

def get_session_cart():
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']

def merge_carts_on_login():
    """
    Called immediately after successful login to merge session cart into db.
    """
    if not current_user.is_authenticated or 'cart' not in session:
        return
        
    session_cart = session['cart']
    for prod_id_str, qty in list(session_cart.items()):
        try:
            prod_id = int(prod_id_str)
            # Check if already in db cart
            db_item = CartItem.query.filter_by(user_id=current_user.id, product_id=prod_id).first()
            if db_item:
                db_item.quantity += qty
            else:
                new_item = CartItem(user_id=current_user.id, product_id=prod_id, quantity=qty)
                db.session.add(new_item)
        except ValueError:
            pass
            
    db.session.commit()
    session.pop('cart', None)

@cart_bp.route('/cart')
def view_cart():
    cart_items_data = []
    subtotal = 0.00
    
    if current_user.is_authenticated and not session.get('is_admin'):
        # Logged in: fetch from database
        db_items = CartItem.query.filter_by(user_id=current_user.id).all()
        for item in db_items:
            price = float(item.product.get_price)
            item_total = price * item.quantity
            subtotal += item_total
            cart_items_data.append({
                'id': item.id,
                'product_id': item.product.id,
                'name': item.product.name,
                'product_code': item.product.product_code,
                'slug': item.product.slug,
                'price': price,
                'image_path': item.product.primary_image_url,
                'quantity': item.quantity,
                'stock_quantity': item.product.stock_quantity,
                'total': item_total
            })
    else:
        # Guest: fetch from session
        session_cart = get_session_cart()
        for prod_id_str, qty in session_cart.items():
            prod = Product.query.get(int(prod_id_str))
            if prod:
                price = float(prod.get_price)
                item_total = price * qty
                subtotal += item_total
                cart_items_data.append({
                    'id': None, # Session item has no db cart ID
                    'product_id': prod.id,
                    'name': prod.name,
                    'product_code': prod.product_code,
                    'slug': prod.slug,
                    'price': price,
                    'image_path': prod.primary_image_url,
                    'quantity': qty,
                    'stock_quantity': prod.stock_quantity,
                    'total': item_total
                })
                
    return render_template('main/cart.html', cart_items=cart_items_data, subtotal=subtotal)

@cart_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', default=1, type=int)
    
    if not product_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'Invalid product or quantity'}), 400
        
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
        
    if product.stock_quantity < quantity:
        return jsonify({'success': False, 'message': f'Only {product.stock_quantity} item(s) in stock'}), 400

    if current_user.is_authenticated and not session.get('is_admin'):
        # Database Cart
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if item:
            if item.quantity + quantity > product.stock_quantity:
                return jsonify({'success': False, 'message': f'Cannot add more. Only {product.stock_quantity} available in stock.'}), 400
            item.quantity += quantity
        else:
            item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
            db.session.add(item)
        db.session.commit()
    else:
        # Session Cart
        session_cart = get_session_cart()
        prod_id_str = str(product_id)
        current_qty = session_cart.get(prod_id_str, 0)
        if current_qty + quantity > product.stock_quantity:
            return jsonify({'success': False, 'message': f'Cannot add more. Only {product.stock_quantity} available in stock.'}), 400
        session_cart[prod_id_str] = current_qty + quantity
        session.modified = True
        
    return jsonify({
        'success': True, 
        'message': f'{product.name} added to cart successfully!',
        'cart_count': len(session['cart']) if not current_user.is_authenticated else CartItem.query.filter_by(user_id=current_user.id).count()
    })

@cart_bp.route('/cart/update', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int)
    
    if not product_id or quantity <= 0:
        return jsonify({'success': False, 'message': 'Invalid parameters'}), 400
        
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
        
    if product.stock_quantity < quantity:
        return jsonify({'success': False, 'message': f'Only {product.stock_quantity} items in stock.'}), 400

    if current_user.is_authenticated and not session.get('is_admin'):
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if item:
            item.quantity = quantity
            db.session.commit()
            item_total = float(product.get_price) * quantity
        else:
            return jsonify({'success': False, 'message': 'Cart item not found'}), 404
    else:
        session_cart = get_session_cart()
        prod_id_str = str(product_id)
        if prod_id_str in session_cart:
            session_cart[prod_id_str] = quantity
            session.modified = True
            item_total = float(product.get_price) * quantity
        else:
            return jsonify({'success': False, 'message': 'Cart item not found'}), 404
            
    # Calculate new subtotal
    subtotal = 0.0
    if current_user.is_authenticated:
        subtotal = sum([float(i.product.get_price) * i.quantity for i in CartItem.query.filter_by(user_id=current_user.id).all()])
    else:
        for p_id, q in session_cart.items():
            p = Product.query.get(int(p_id))
            if p:
                subtotal += float(p.get_price) * q
                
    return jsonify({
        'success': True,
        'item_total': item_total,
        'subtotal': subtotal
    })

@cart_bp.route('/cart/remove/<int:product_id>', methods=['POST', 'GET'])
def remove_from_cart(product_id):
    if current_user.is_authenticated and not session.get('is_admin'):
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            flash('Item removed from cart.', 'success')
    else:
        session_cart = get_session_cart()
        prod_id_str = str(product_id)
        if prod_id_str in session_cart:
            session_cart.pop(prod_id_str)
            session.modified = True
            flash('Item removed from cart.', 'success')
            
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/wishlist')
@login_required
def view_wishlist():
    if session.get('is_admin'):
        flash('Admins cannot access wishlists.', 'warning')
        return redirect(url_for('admin.dashboard'))
    wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('main/wishlist.html', wishlist_items=wishlist_items)

@cart_bp.route('/wishlist/add', methods=['POST'])
@login_required
def add_to_wishlist():
    if session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Admins cannot use wishlists'}), 400
        
    product_id = request.form.get('product_id', type=int)
    if not product_id:
        return jsonify({'success': False, 'message': 'Invalid product ID'}), 400
        
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
        
    # Check if already in wishlist
    existing = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        return jsonify({'success': True, 'message': 'Product already in wishlist!'})
        
    new_wish = WishlistItem(user_id=current_user.id, product_id=product_id)
    db.session.add(new_wish)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Product added to wishlist!'})

@cart_bp.route('/wishlist/remove/<int:product_id>', methods=['POST', 'GET'])
@login_required
def remove_from_wishlist(product_id):
    wish_item = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if wish_item:
        db.session.delete(wish_item)
        db.session.commit()
        flash('Item removed from wishlist.', 'success')
    return redirect(url_for('cart.view_wishlist'))
