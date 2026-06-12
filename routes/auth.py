from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Order, WishlistItem
from utils.security import validate_email, validate_password, validate_phone
import random
from datetime import datetime, timedelta
import requests

auth_bp = Blueprint('auth', __name__)

def verify_firebase_token(id_token):
    api_key = current_app.config.get('FIREBASE_API_KEY')
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}"
    payload = {"idToken": id_token}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "users" in data and len(data["users"]) > 0:
                return data["users"][0]
        return None
    except Exception as e:
        current_app.logger.error(f"Firebase token verification failed: {e}")
        return None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated and not session.get('is_admin'):
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        firebase_id_token = request.form.get('firebase_id_token')
        if not firebase_id_token:
            flash('JavaScript and Firebase authentication are required.', 'danger')
            return render_template('auth/register.html')
            
        decoded_token = verify_firebase_token(firebase_id_token)
        if not decoded_token:
            flash('Invalid or expired authentication token. Please try again.', 'danger')
            return render_template('auth/register.html')
            
        email = decoded_token.get('email')
        if not email:
            flash('Unable to retrieve email from token.', 'danger')
            return render_template('auth/register.html')
            
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # fallback to token display name if form inputs are somehow missing
        display_name = decoded_token.get('displayName', '')
        if not first_name and display_name:
            parts = display_name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''
            
        if not first_name:
            first_name = email.split('@')[0]
            
        existing_user = User.query.filter_by(email=email).first()
        if not existing_user:
            # Create user
            new_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone
            )
            # Set random password since it is authenticated by Firebase
            import uuid
            new_user.set_password(uuid.uuid4().hex)
            
            try:
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                session['is_admin'] = False
                
                # Merge guest cart
                try:
                    from routes.cart import merge_carts_on_login
                    merge_carts_on_login()
                except Exception as e:
                    current_app.logger.error(f"Error merging cart on register: {e}")
                    
                flash('Registration and sign in successful!', 'success')
                return redirect(url_for('main.index'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating user: {e}")
                flash('An error occurred during account setup. Please try again.', 'danger')
                return render_template('auth/register.html')
        else:
            # User already exists in SQLite
            login_user(existing_user)
            session['is_admin'] = False
            
            # Merge guest cart
            try:
                from routes.cart import merge_carts_on_login
                merge_carts_on_login()
            except Exception as e:
                current_app.logger.error(f"Error merging cart on register: {e}")
                
            flash('You are already registered and now signed in.', 'success')
            return redirect(url_for('main.index'))
            
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if session.get('is_admin'):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        firebase_id_token = request.form.get('firebase_id_token')
        remember = True if request.form.get('remember') else False
        
        if not firebase_id_token:
            flash('JavaScript and Firebase authentication are required.', 'danger')
            return render_template('auth/login.html')
            
        decoded_token = verify_firebase_token(firebase_id_token)
        if not decoded_token:
            flash('Invalid or expired authentication token. Please try again.', 'danger')
            return render_template('auth/login.html')
            
        email = decoded_token.get('email')
        if not email:
            flash('Unable to retrieve email from token.', 'danger')
            return render_template('auth/login.html')
            
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # The database must have been reset on Render. Recreate user on-the-fly!
            display_name = decoded_token.get('displayName', '')
            if display_name:
                parts = display_name.split(' ', 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ''
            else:
                first_name = email.split('@')[0]
                last_name = ''
                
            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=''
            )
            import uuid
            user.set_password(uuid.uuid4().hex)
            
            try:
                db.session.add(user)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error recreating user on login: {e}")
                flash('An error occurred during account login setup. Please try again.', 'danger')
                return render_template('auth/login.html')
                
        session['is_admin'] = False # Ensure not treated as admin
        login_user(user, remember=remember)
        
        # Merge guest cart
        try:
            from routes.cart import merge_carts_on_login
            merge_carts_on_login()
        except Exception as e:
            current_app.logger.error(f"Error merging cart on login: {e}")
            
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.index'))
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('is_admin', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))




@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if session.get('is_admin'):
        flash('Admins cannot access user profiles.', 'warning')
        return redirect(url_for('admin.dashboard'))
        
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    
    if request.method == 'POST':
        # Check if updating password or general profile details
        action = request.form.get('action')
        
        if action == 'update_profile':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            
            if not first_name or not last_name:
                flash('First name and last name are required.', 'danger')
                return render_template('auth/profile.html', orders=orders, wishlist_items=wishlist_items)
                
            if not validate_phone(phone):
                flash('Invalid phone format.', 'danger')
                return render_template('auth/profile.html', orders=orders, wishlist_items=wishlist_items)
                
            current_user.first_name = first_name
            current_user.last_name = last_name
            current_user.phone = phone
            
            try:
                db.session.commit()
                flash('Profile details updated successfully.', 'success')
            except Exception:
                db.session.rollback()
                flash('Error updating profile.', 'danger')
                
        elif action == 'change_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not current_user.check_password(old_password):
                flash('Incorrect current password.', 'danger')
                return render_template('auth/profile.html', orders=orders, wishlist_items=wishlist_items)
                
            if not validate_password(new_password):
                flash('New password does not meet requirements.', 'danger')
                return render_template('auth/profile.html', orders=orders, wishlist_items=wishlist_items)
                
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return render_template('auth/profile.html', orders=orders, wishlist_items=wishlist_items)
                
            current_user.set_password(new_password)
            try:
                db.session.commit()
                flash('Password changed successfully.', 'success')
            except Exception:
                db.session.rollback()
                flash('Error changing password.', 'danger')
                
    return render_template('auth/profile.html', orders=orders, wishlist_items=wishlist_items)





