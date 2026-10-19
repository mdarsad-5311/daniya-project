# Glow & Pure — E-Commerce Web Application

A full-featured e-commerce platform built with Django, Tailwind CSS, and Alpine.js, featuring product management, shopping cart, wishlist, customer order tracking, and Razorpay payment integration.

---

## Features

- **Product Discovery & Catalog**: Categorized product listings, search filters, and rich product detail pages.
- **Cart & Wishlist**: Session-based guest cart with seamless transition upon authentication, plus user wishlist management.
- **Checkout & Payments**: Secure checkout with Razorpay test/live payment integration, server-side signature verification, and webhook handling.
- **User Accounts**: Registration, login, profile management, and complete order history tracking.
- **Reviews & Ratings**: Verified customer product feedback and ratings.
- **Store Administration**: Standard Django admin for order management, product catalogs, customer messages, and stock control.
- **Modern UI**: Responsive mobile-first interface styled with Tailwind CSS and interactive micro-interactions powered by Alpine.js.

---

## Tech Stack

- **Backend**: Python 3, Django (MTV architecture)
- **Database**: SQLite (Development / Testing) / PostgreSQL compatible
- **Frontend**: Django Templates, HTML5, Tailwind CSS, Alpine.js
- **Payment Gateway**: Razorpay SDK
- **Static Assets**: WhiteNoise for production static file serving

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js & npm (for Tailwind CSS compilation)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/mdarsad-5311/daniya-project.git
cd daniya-project
```

### 2. Set up virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the sample environment file and update the configuration values as needed:

```bash
cp .env.example .env
```

Key environment variables:
- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `True` for local development
- `ALLOWED_HOSTS`: Comma-separated list of allowed hostnames
- `RAZORPAY_KEY_ID`: Razorpay public API key
- `RAZORPAY_KEY_SECRET`: Razorpay secret API key

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. (Optional) Compile CSS assets

If you modify styling in `static_src/css/style.css`, rebuild the Tailwind bundle:

```bash
npm install
npm run build:css
```

### 7. Run the development server

```bash
python manage.py runserver
```

Access the application in your browser at `http://127.0.0.1:8000/`.

---

## Running Tests

Execute the automated test suite:

```bash
python manage.py test
```

---

## Project Structure

```text
daniya-project/
├── accounts/          # User authentication and profile views
├── cart/              # Cart management and session handling
├── categories/        # Product categories and listings
├── daniya_project/    # Project settings, URLs, WSGI/ASGI configuration
├── orders/            # Order placement and history management
├── payment/           # Razorpay integration and webhooks
├── products/          # Product catalog, details, reviews
├── wishlist/          # User wishlist functionality
├── static/            # Compiled static assets (CSS, JS, images)
├── static_src/        # Source styling (Tailwind CSS)
├── templates/         # Django HTML templates
├── manage.py          # Django administrative CLI
└── requirements.txt   # Python package dependencies
```

---

## Deployment

Refer to [`DEPLOYMENT.md`](DEPLOYMENT.md) for production environment configuration and [`PAYMENT.md`](PAYMENT.md) for payment gateway webhook instructions.
