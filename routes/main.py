from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from models import db, Product, Category, Review, Order, Banner
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    categories = Category.query.all()
    # Fetch 8 newest products for "New Arrivals"
    new_arrivals = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    # Fetch 4 discounted products for "Special Offers"
    special_offers = Product.query.filter(Product.discount_price.isnot(None)).limit(4).all()
    banners = Banner.query.order_by(Banner.created_at.asc()).all()
    return render_template('main/index.html', categories=categories, new_arrivals=new_arrivals, special_offers=special_offers, banners=banners)

@main_bp.route('/shop')
@main_bp.route('/shop/<category_slug>')
def shop(category_slug=None):
    query = Product.query
    
    # Filter by category slug if provided in URL or query parameter
    cat_slug = category_slug or request.args.get('category')
    selected_category = None
    if cat_slug:
        selected_category = Category.query.filter_by(slug=cat_slug).first()
        if selected_category:
            query = query.filter_by(category_id=selected_category.id)
            
    # Filter by Search term
    search_term = request.args.get('search', '').strip()
    if search_term:
        query = query.filter(
            (Product.name.like(f"%{search_term}%")) | 
            (Product.description.like(f"%{search_term}%")) |
            (Product.product_code.like(f"%{search_term}%")) |
            (Product.material.like(f"%{search_term}%")) |
            (Product.color.like(f"%{search_term}%"))
        )
        
    # Filter by Price range
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    
    try:
        if min_price:
            query = query.filter(Product.price >= float(min_price))
        if max_price:
            query = query.filter(Product.price <= float(max_price))
    except ValueError:
        pass
        
    # Sort option
    sort_by = request.args.get('sort', 'newest')
    if sort_by == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'popular':
        # Simple popularity metric: based on number of reviews
        query = query.outerjoin(Review).group_by(Product.id).order_by(db.func.count(Review.id).desc())
    else:
        query = query.order_by(Product.created_at.desc())
        
    products = query.all()
    categories = Category.query.all()
    
    return render_template('main/shop.html', 
                           products=products, 
                           categories=categories, 
                           selected_category=selected_category,
                           search_term=search_term,
                           min_price=min_price,
                           max_price=max_price,
                           sort_by=sort_by)

@main_bp.route('/product/<slug>', methods=['GET', 'POST'])
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    categories = Category.query.all()
    
    # Handle Review Submission
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('You must be logged in to write a review.', 'danger')
            return redirect(url_for('auth.login'))
            
        rating = request.form.get('rating')
        review_text = request.form.get('review_text', '').strip()
        
        # Verify user has purchased the product (Optional but good for premium commerce)
        # For simplicity, we check if user is logged in
        if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
            flash('Please select a valid rating (1 to 5).', 'danger')
            return redirect(url_for('main.product_detail', slug=slug))
            
        # Check if user already reviewed
        existing_review = Review.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if existing_review:
            existing_review.rating = int(rating)
            existing_review.review_text = review_text
            existing_review.created_at = datetime.utcnow()
            flash('Your review has been updated.', 'success')
        else:
            new_review = Review(
                user_id=current_user.id,
                product_id=product.id,
                rating=int(rating),
                review_text=review_text
            )
            db.session.add(new_review)
            flash('Thank you for your review!', 'success')
            
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Error saving review.', 'danger')
            
        return redirect(url_for('main.product_detail', slug=slug))
        
    # Get related products (same category, excluding current product)
    related_products = Product.query.filter(
        Product.category_id == product.category_id, 
        Product.id != product.id
    ).limit(4).all()
    
    # Calculate average rating
    avg_rating = 0.0
    reviews = product.reviews
    if reviews:
        avg_rating = sum([r.rating for r in reviews]) / len(reviews)
        
    return render_template('main/product_detail.html', 
                           product=product, 
                           related_products=related_products, 
                           avg_rating=round(avg_rating, 1),
                           reviews=reviews)

@main_bp.route('/contact')
def contact():
    return render_template('main/contact.html')

@main_bp.route('/about')
def about():
    return render_template('main/about.html')

@main_bp.route('/robots.txt')
def robots():
    content = "User-agent: *\nDisallow: /admin/\nDisallow: /cart\nDisallow: /checkout\nSitemap: http://ps-tex.com/sitemap.xml"
    return Response(content, mimetype="text/plain")

@main_bp.route('/sitemap.xml')
def sitemap():
    pages = []
    
    # Static pages
    pages.append({'loc': url_for('main.index', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')})
    pages.append({'loc': url_for('main.contact', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')})
    pages.append({'loc': url_for('main.about', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')})
    pages.append({'loc': url_for('main.shop', _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')})
    
    # Category pages
    categories = Category.query.all()
    for cat in categories:
        pages.append({'loc': url_for('main.shop', category_slug=cat.slug, _external=True), 'lastmod': datetime.now().strftime('%Y-%m-%d')})
        
    # Product pages
    products = Product.query.all()
    for prod in products:
        pages.append({'loc': url_for('main.product_detail', slug=prod.slug, _external=True), 'lastmod': prod.created_at.strftime('%Y-%m-%d')})
        
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')
