from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Order, WishlistItem
from utils.security import validate_email, validate_password, validate_phone
import random
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated and not session.get('is_admin'):
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not first_name or not last_name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')
            
        if not validate_email(email):
            flash('Invalid email address format.', 'danger')
            return render_template('auth/register.html')
            
        if not validate_phone(phone):
            flash('Invalid phone number format. Please provide a 10-12 digit number.', 'danger')
            return render_template('auth/register.html')
            
        if not validate_password(password):
            flash('Password must be at least 8 characters long and contain a letter, a number, and a special character.', 'danger')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
            
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address is already registered.', 'danger')
            return render_template('auth/register.html')
            
        # Create user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if session.get('is_admin'):
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')
            
        session['is_admin'] = False # Ensure not treated as admin
        login_user(user, remember=remember)
        
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





