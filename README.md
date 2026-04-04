# Campus Lost & Found

A production-ready Django web application for campus communities to report, search, and recover lost items.

## Features

- **Authentication**: Register, login, logout, password reset via email
- **Item Management**: Report lost/found items with title, description, category, location, date, image
- **Search & Filter**: Keyword search, filter by type/category/status, paginated results
- **Smart Matching**: Automatically finds possible matches (opposite type, same category, keyword overlap)
- **Contact**: Email-based contact between users
- **Admin Panel**: Full Django admin with custom filters and bulk actions
- **Responsive**: Works on mobile and desktop (Bootstrap 5)
- **Secure**: CSRF protection, XSS prevention, secure password storage, input validation

## Quick Start (Local Development)

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd campus_lostfound

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your values

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Run development server
python manage.py runserver
```

Visit http://127.0.0.1:8000 — Admin at http://127.0.0.1:8000/admin/

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | Yes | True/False |
| `ALLOWED_HOSTS` | Yes | Comma-separated hosts |
| `DATABASE_URL` | Production | PostgreSQL URL |
| `EMAIL_HOST` | Production | SMTP host |
| `EMAIL_HOST_USER` | Production | SMTP username |
| `EMAIL_HOST_PASSWORD` | Production | SMTP password |
| `USE_S3` | Optional | True to use S3 for media |
| `AWS_ACCESS_KEY_ID` | If USE_S3 | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | If USE_S3 | AWS secret key |
| `AWS_STORAGE_BUCKET_NAME` | If USE_S3 | S3 bucket name |

## Running Tests

```bash
python manage.py test
```

Tests cover: authentication, item creation, search/filter, matching logic, authorization rules.

## Deployment on Render

1. Push code to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Set environment variables in the Render dashboard
4. Render will auto-deploy using `render.yaml`

**Build command:**
```
pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate
```

**Start command:**
```
gunicorn campus_lostfound.wsgi:application
```

## Deployment on Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

railway login
railway init
railway add postgresql
railway up
```

Set environment variables via `railway variables set KEY=VALUE`.

## Production Checklist

- [ ] `DEBUG=False`
- [ ] Strong `SECRET_KEY` in environment variable
- [ ] `ALLOWED_HOSTS` set to your domain
- [ ] PostgreSQL `DATABASE_URL` configured
- [ ] Email credentials set (`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`)
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] HTTPS configured (handled by Render/Railway/Heroku)
- [ ] Create superuser: `python manage.py createsuperuser`

## Project Structure

```
campus_lostfound/
├── campus_lostfound/     # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── items/                # Core app
│   ├── models.py         # Item model with matching logic
│   ├── views.py          # All item views
│   ├── forms.py          # Item and search forms
│   ├── admin.py          # Admin configuration
│   ├── urls.py
│   ├── tests.py          # Comprehensive tests
│   └── templatetags/
├── accounts/             # Auth app
│   ├── views.py
│   ├── forms.py
│   └── urls.py
├── templates/            # HTML templates
│   ├── base.html
│   ├── items/
│   ├── accounts/
│   └── registration/
├── static/               # CSS, JS, images
├── requirements.txt
├── Procfile
├── render.yaml
└── .env.example
```

## Database Backup

For PostgreSQL on Render/Railway, enable automatic daily backups in the dashboard.

Manual backup:
```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

Restore:
```bash
psql $DATABASE_URL < backup_20250101.sql
```
