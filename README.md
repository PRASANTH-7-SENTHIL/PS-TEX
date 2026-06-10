# PS-TEX Premium Saree Store E-Commerce Web App

A complete, production-ready, beautiful e-commerce web application for **PS-TEX**, built with Flask, MySQL, and Razorpay.

## Features

- **Premium Branding Theme**: Curated Maroon and Gold color palette, custom logo and traditional dividers, Playfair Display typography.
- **Dynamic Cart & Wishlist**: Dynamic quantities updates, guest cart sessions which merge into database records upon registration/login.
- **Razorpay Checkout Integration**: Client-side checkout modal popups with secure server-side signature checks, stock subtraction on successful pay status, transaction records log, and success/failure ticketing.
- **Protected Administrator Panel**: Dashboard statistics, dynamic revenue reports, customer index, category CRUD, orders tracking management, settings editor, and product management (supporting multiple image uploads and primary picture settings).
- **SEO & Clean URLs**: Clean `/shop/<category_slug>` and `/product/<product_slug>` routes, dynamic meta titles and descriptions, `/robots.txt`, and dynamic `/sitemap.xml`.
- **Production-Ready Security**: Passwords hashed securely using scrypt, CSRF protection, admin blueprint check middleware, local upload checks (extensions & sizes).

---

## Folder Structure

```
project/ (Workspace root)
├── app.py                   # Flask App Factory and entry point
├── config.py                # Environment configurations
├── requirements.txt         # Package dependencies
├── database.sql             # Raw MySQL Schema dump
├── DEPLOYMENT.md            # Hostinger VPS deployment guide
├── models.py                # SQLAlchemy Models (all tables)
├── .env                     # Local environment settings
│
├── routes/                  # Blueprint routes
│   ├── auth.py              # User authentication
│   ├── main.py              # Home, Shop, Details, static files
│   ├── cart.py              # Cart & Wishlist
│   ├── checkout.py          # Checkout and Razorpay payments
│   └── admin.py             # Admin panel operations
│
├── templates/               # Jinja2 templates
│   ├── base.html            # Core layout page
│   ├── main/                # Index, shop, product, about, contact
│   ├── auth/                # Login, register, forgot, profile
│   ├── checkout/            # Checkout views, success, failure
│   └── admin/               # Admin dashboard, products, orders, settings
│
├── static/                  # Static assets
│   ├── css/style.css        # Premium custom styles (Maroon, Gold)
│   ├── js/main.js           # General JS (form checkers)
│   └── js/cart.js           # Cart & Wishlist AJAX scripts
│
└── utils/                   # Helper utilities
    ├── helpers.py           # Slugs, local image saving
    └── security.py          # Input validation
```

---

## Local Installation

### 1. Set up Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate   # On Linux/macOS
```

### 2. Install Packages
```bash
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
python app.py
```

Upon starting, Flask will automatically create a local SQLite database file `pstex.db` (if MySQL variables in `.env` are empty) and auto-seed:
- The Admin Account: `prasanth1619@gmail.com` with password `@Prasanth1619`
- Fabric categories: Kanchipuram Silk, Banarasi Silk, Samuthrika Saree, Cotton Saree.
- Default discount coupon: `PSTEX10` (10% off for carts > ₹1500).

To use MySQL locally, open `.env` and fill out `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, and `MYSQL_DB`.

---

## Administrator Login
- URL: `/admin/login`
- Email: `prasanth1619@gmail.com`
- Password: `@Prasanth1619`
*(Can be updated in settings under `/admin/settings`)*

---

## Deployment to Hostinger VPS
For deployment commands, virtual environments, systemd background daemons, Nginx reverse proxies, and Certbot SSL certificate setups, consult [DEPLOYMENT.md](file:///c:/Users/Prasanth%20S/OneDrive/Documents/PS%20TEX/DEPLOYMENT.md).
