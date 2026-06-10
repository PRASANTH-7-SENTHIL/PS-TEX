# Production Deployment Guide: PS-TEX Saree Store on Hostinger VPS

This guide outlines step-by-step instructions for deploying the **PS-TEX** Flask application on a Hostinger VPS running **Ubuntu 22.04 LTS** with **MySQL**, **Gunicorn**, and **Nginx**.

---

## 1. System Updates & Core Packages

First, log in to your Hostinger VPS via SSH and update the system package indexes:

```bash
sudo apt update && sudo apt upgrade -y
```

Install python, pip, git, nginx, and MySQL utilities:

```bash
sudo apt install python3-pip python3-dev python3-venv mysql-server nginx git curl -y
```

---

## 2. MySQL Database Setup

Secure the MySQL installation:

```bash
sudo mysql_secure_installation
```

Log in to the MySQL command line as root:

```bash
sudo mysql
```

Run the following SQL commands to create the database and dedicate a database user:

```sql
CREATE DATABASE pstex_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'pstex_user'@'localhost' IDENTIFIED BY 'YourSecureDatabasePassword123!';

GRANT ALL PRIVILEGES ON pstex_db.* TO 'pstex_user'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

> [!TIP]
> You can import the raw schema `database.sql` directly using command line:
> `mysql -u pstex_user -p pstex_db < /path/to/project/database.sql`

---

## 3. Clone & Project Initialization

Navigate to the directory where you want to keep the application (typically `/var/www/`):

```bash
sudo mkdir -p /var/www/ps-tex
sudo chown -R $USER:$USER /var/www/ps-tex
cd /var/www/ps-tex
```

Clone or upload your project code here. 
Initialize a Python virtual environment and activate it:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the project dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
pip install gunicorn
```

---

## 4. Production Environment Configuration

Create a `.env` file inside `/var/www/ps-tex/` to store credentials securely:

```env
SECRET_KEY=pstex-production-secret-9876-1234
MYSQL_USER=pstex_user
MYSQL_PASSWORD=YourSecureDatabasePassword123!
MYSQL_HOST=localhost
MYSQL_DB=pstex_db
RAZORPAY_KEY_ID=rzp_live_SyKZjPt2aMAILV
RAZORPAY_KEY_SECRET=6kS0TtrTavkpeVcYylSXFN1R
SESSION_COOKIE_SECURE=True
```

---

## 5. Systemd Gunicorn Service

We will configure Systemd to run Gunicorn in the background as a daemon and restart automatically on server reboot.

Create the service file:

```bash
sudo nano /etc/systemd/system/pstex.service
```

Paste the following configurations:

```ini
[Unit]
Description=Gunicorn instance to serve PS-TEX Flask Web Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ps-tex
Environment="PATH=/var/www/ps-tex/venv/bin"
ExecStart=/var/www/ps-tex/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 "app:create_app()"

[Install]
WantedBy=multi-user.target
```

Give the web server user ownership of the project files so Gunicorn can write uploads:

```bash
sudo chown -R www-data:www-data /var/www/ps-tex
```

Start the service and enable it to run at boot:

```bash
sudo systemctl start pstex
sudo systemctl enable pstex
```

---

## 6. Nginx Reverse Proxy & Static Optimization

Configure Nginx to proxy connections to Gunicorn and serve the `uploads/` directory directly for maximum static speed and caching.

Create the site configuration:

```bash
sudo nano /etc/nginx/sites-available/ps-tex
```

Paste the following server block:

```nginx
server {
    listen 80;
    server_name ps-tex.com www.ps-tex.com;

    # Serve uploads directly via Nginx instead of passing to Flask (faster!)
    location /uploads/ {
        alias /var/www/ps-tex/uploads/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Serve static assets (CSS, JS, SVG) directly
    location /static/ {
        alias /var/www/ps-tex/static/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Reverse proxy connection to Gunicorn
    location / {
        include proxy_params;
        proxy_pass http://127.0.0.1:5000;
        proxy_redirect off;
        
        # Enable large uploads for saree photos
        client_max_body_size 16M;
    }
}
```

Enable the configuration and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/ps-tex /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 7. SSL Certificate Setup (HTTPS)

Secure the website by installing a free SSL certificate from Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d ps-tex.com -d www.ps-tex.com
```

Certbot will automatically verify ownership, fetch the certificate, and update the Nginx configuration to support SSL and auto-redirect HTTP to HTTPS.

Verify that the systemd auto-renewal service is running:

```bash
sudo systemctl status certbot.timer
```
