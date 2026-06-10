import uuid
import razorpay
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from models import db, Product, CartItem, Order, OrderItem, Payment, Coupon
from datetime import datetime

checkout_bp = Blueprint('checkout', __name__)

def get_razorpay_client():
    return razorpay.Client(auth=(
        current_app.config['RAZORPAY_KEY_ID'], 
        current_app.config['RAZORPAY_KEY_SECRET']
    ))

@checkout_bp.route('/checkout')
@login_required
def index():
    if session.get('is_admin'):
        flash('Admins cannot make purchases.', 'warning')
        return redirect(url_for('admin.dashboard'))
        
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('cart.view_cart'))
        
    # Check stock first
    for item in cart_items:
        if item.product.stock_quantity < item.quantity:
            flash(f'Product {item.product.name} only has {item.product.stock_quantity} item(s) in stock. Please adjust your cart.', 'danger')
            return redirect(url_for('cart.view_cart'))
            
    subtotal = sum([float(item.product.get_price) * item.quantity for item in cart_items])
    
    # Check if coupon is applied in session
    coupon_code = session.get('applied_coupon')
    discount = 0.00
    coupon_id = None
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon and coupon.is_valid(subtotal):
            discount = float(coupon.calculate_discount(subtotal))
            coupon_id = coupon.id
        else:
            session.pop('applied_coupon', None)
            
    grand_total = max(subtotal - discount, 0.00)
    
    return render_template('checkout/checkout.html', 
                           cart_items=cart_items, 
                           subtotal=subtotal, 
                           discount=discount, 
                           coupon_code=coupon_code,
                           grand_total=grand_total)

@checkout_bp.route('/checkout/apply-coupon', methods=['POST'])
@login_required
def apply_coupon():
    code = request.form.get('coupon_code', '').strip().upper()
    if not code:
        return jsonify({'success': False, 'message': 'Coupon code is required.'})
        
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({'success': False, 'message': 'Cart is empty.'})
        
    subtotal = sum([float(item.product.get_price) * item.quantity for item in cart_items])
    coupon = Coupon.query.filter_by(code=code).first()
    
    if not coupon:
        return jsonify({'success': False, 'message': 'Invalid coupon code.'})
        
    if not coupon.is_valid(subtotal):
        return jsonify({'success': False, 'message': f'Coupon is not applicable. Min amount required is ₹{coupon.min_cart_amount}.'})
        
    discount = float(coupon.calculate_discount(subtotal))
    session['applied_coupon'] = code
    grand_total = max(subtotal - discount, 0.00)
    
    return jsonify({
        'success': True,
        'message': f'Coupon "{code}" applied successfully!',
        'discount': discount,
        'grand_total': grand_total
    })

@checkout_bp.route('/checkout/remove-coupon', methods=['POST'])
@login_required
def remove_coupon():
    session.pop('applied_coupon', None)
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum([float(item.product.get_price) * item.quantity for item in cart_items])
    return jsonify({
        'success': True,
        'message': 'Coupon removed.',
        'grand_total': subtotal
    })

@checkout_bp.route('/checkout/create-order', methods=['POST'])
@login_required
def create_order():
    """
    Step 1: Save the shipping details, create a database order, 
    and fetch a Razorpay Order ID.
    """
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    shipping_address = request.form.get('address', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    pincode = request.form.get('pincode', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    
    if not first_name or not last_name or not shipping_address or not city or not state or not pincode or not phone or not email:
        return jsonify({'success': False, 'message': 'All shipping fields are required.'}), 400
        
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({'success': False, 'message': 'Your cart is empty.'}), 400
        
    # Verify stock before placing order
    for item in cart_items:
        if item.product.stock_quantity < item.quantity:
            return jsonify({'success': False, 'message': f'Product {item.product.name} is out of stock.'}), 400
            
    subtotal = sum([float(item.product.get_price) * item.quantity for item in cart_items])
    
    # Calculate coupon discount
    discount = 0.00
    coupon_code = session.get('applied_coupon')
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon and coupon.is_valid(subtotal):
            discount = float(coupon.calculate_discount(subtotal))
            
    grand_total = max(subtotal - discount, 0.00)
    
    # Generate unique order number
    order_number = f"PSTEX-{uuid.uuid4().hex[:8].upper()}"
    
    # Create DB Order (Status: Pending Payment)
    db_order = Order(
        order_number=order_number,
        user_id=current_user.id,
        total_amount=grand_total,
        discount_amount=discount,
        shipping_address=shipping_address,
        city=city,
        state=state,
        pincode=pincode,
        phone=phone,
        email=email,
        order_status='Pending'
    )
    db.session.add(db_order)
    
    # Create Order Items
    for item in cart_items:
        order_item = OrderItem(
            order=db_order,
            product_id=item.product.id,
            quantity=item.quantity,
            price=item.product.get_price
        )
        db.session.add(order_item)
        
    try:
        # Create Razorpay Order
        client = get_razorpay_client()
        amount_paise = int(grand_total * 100) # Razorpay expects paise
        razorpay_data = {
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': order_number,
            'payment_capture': 1 # Auto capture
        }
        razorpay_order = client.order.create(data=razorpay_data)
        
        db_order.razorpay_order_id = razorpay_order['id']
        db.session.commit()
        
        return jsonify({
            'success': True,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': current_app.config['RAZORPAY_KEY_ID'],
            'amount': amount_paise,
            'order_number': order_number,
            'name': f"{first_name} {last_name}",
            'email': email,
            'phone': phone
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Razorpay API error: {str(e)}'}), 500

@checkout_bp.route('/checkout/verify', methods=['POST'])
@login_required
def verify_payment():
    """
    Step 2: Client sends signature verification token.
    Check it via SDK and convert order to Paid.
    """
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_signature = request.form.get('razorpay_signature')
    
    if not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return jsonify({'success': False, 'message': 'Payment details missing.'}), 400
        
    db_order = Order.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not db_order:
        return jsonify({'success': False, 'message': 'Order not found.'}), 404
        
    try:
        # Verify payment signature
        client = get_razorpay_client()
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        client.utility.verify_payment_signature(params_dict)
        
        # If verification is successful, change order status to Paid
        db_order.order_status = 'Paid'
        
        # Deduct stocks
        for item in db_order.items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity = max(product.stock_quantity - item.quantity, 0)
                if product.stock_quantity == 0:
                    product.availability_status = 'Out of Stock'
                    
        # Log payment detail
        payment = Payment(
            order_id=db_order.id,
            transaction_id=razorpay_payment_id,
            payment_method='Razorpay',
            amount=db_order.total_amount,
            status='Captured'
        )
        db.session.add(payment)
        
        # Clear database cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        
        # Clear applied coupon from session
        session.pop('applied_coupon', None)
        
        db.session.commit()
        return jsonify({'success': True, 'order_number': db_order.order_number})
        
    except razorpay.errors.SignatureVerificationError:
        # Log failed payment attempt in order status
        db_order.order_status = 'Payment Failed'
        
        payment = Payment(
            order_id=db_order.id,
            transaction_id=razorpay_payment_id,
            payment_method='Razorpay',
            amount=db_order.total_amount,
            status='Failed'
        )
        db.session.add(payment)
        db.session.commit()
        return jsonify({'success': False, 'message': 'Payment signature verification failed.'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@checkout_bp.route('/checkout/success')
@login_required
def payment_success():
    order_num = request.args.get('order_number')
    order = Order.query.filter_by(order_number=order_num, user_id=current_user.id).first_or_404()
    return render_template('checkout/payment_success.html', order=order)

@checkout_bp.route('/checkout/failure')
@login_required
def payment_failure():
    message = request.args.get('message', 'Your transaction could not be processed.')
    return render_template('checkout/payment_failure.html', message=message)
