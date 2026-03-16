# Meadow Shore

Designer clothing brand website built with Django + Wagtail CMS.

**Meadow Shore** is a tactile clothing brand with a natural character — dense T-shirts with realistic forest prints. Silence. Fabric. Forest.

---

## Tech Stack

- **Python** 3.10+
- **Django** 4.2
- **Wagtail** 5.2 (CMS)
- **SQLite** (development) / **PostgreSQL** (production)
- **WhiteNoise** for static files in production
- **Gunicorn** as WSGI server

---

## Local Development Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd meadow-v2
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# On Windows (PowerShell):
venv\Scripts\Activate.ps1

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
SECRET_KEY=your-very-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

The site will be available at: [http://localhost:8000](http://localhost:8000)

The Wagtail admin panel: [http://localhost:8000/admin/](http://localhost:8000/admin/)

---

## Project Structure

```
meadow-v2/
├── meadowshore/          # Django project settings and URLs
│   ├── settings/
│   │   ├── base.py       # Shared settings
│   │   ├── dev.py        # Development settings
│   │   └── production.py # Production settings
│   ├── urls.py
│   └── wsgi.py
├── home/                 # Home page app (Wagtail StreamField)
│   ├── models.py         # HomePage with all StreamField blocks
│   └── templates/
├── website/              # Inner pages app
│   ├── models.py         # AboutPage, CatalogPage, ProductPage, ContactPage
│   └── templates/
├── templates/            # Shared templates
│   ├── base.html
│   └── includes/
│       ├── header.html
│       └── footer.html
├── static/
│   ├── css/style.css     # Complete stylesheet
│   ├── js/main.js        # JavaScript (scroll reveal, mobile menu)
│   └── images/
└── media/                # Uploaded files (not tracked in git)
```

---

## CMS Setup (Wagtail Admin)

After running migrations and creating a superuser:

1. Go to [http://localhost:8000/admin/](http://localhost:8000/admin/)
2. Log in with your superuser credentials
3. In **Settings > Sites**, set up your site root page
4. Create a **Home Page** under the root
5. Add StreamField blocks to the Home page: Hero, About, Collections, Marquee, Features, Fabric, Featured Products, Philosophy, CTA
6. Create inner pages under the Home page:
   - **About Page** (`/about/`)
   - **Catalog Page** (`/collection/`) — add **Product Pages** as children
   - **Contact Page** (`/contact/`) — configure form fields and email settings

---

## Page Types

| Page Type | URL | Description |
|-----------|-----|-------------|
| `HomePage` | `/` | Landing page with StreamField sections |
| `AboutPage` | `/about/` | Brand story and values |
| `CatalogPage` | `/collection/` | Product catalog listing |
| `ProductPage` | `/collection/product-slug/` | Individual product detail |
| `ContactPage` | `/contact/` | Contact form (Wagtail forms) |

---

## StreamField Blocks (Home Page)

| Block | Description |
|-------|-------------|
| `hero` | Full-screen hero with headline, subheadline, CTA, image |
| `about` | About the brand with text, details, image |
| `collections` | Grid of collection cards |
| `marquee` | Animated scrolling text banner |
| `features` | Numbered brand features/advantages |
| `fabric` | Fabric quality section with stats |
| `featured_products` | Grid of featured product cards |
| `philosophy` | Brand philosophy quote section |
| `cta` | Call-to-action section |

---

## Production Deployment

### Environment variables for production

```env
SECRET_KEY=a-very-long-and-random-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:password@host:5432/dbname
```

### Using production settings

```bash
DJANGO_SETTINGS_MODULE=meadowshore.settings.production gunicorn meadowshore.wsgi
```

### Collect static files

```bash
python manage.py collectstatic --noinput
```

### Run migrations on production

```bash
python manage.py migrate
```

---

## Deployment on Railway

1. Push your code to GitHub
2. Create a new Railway project and connect your repository
3. Add a PostgreSQL plugin in Railway
4. Set environment variables in Railway dashboard:
   - `SECRET_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS=your-app.up.railway.app`
   - `DATABASE_URL` (auto-set by Railway PostgreSQL plugin)
   - `DJANGO_SETTINGS_MODULE=meadowshore.settings.production`
5. Railway will automatically build and deploy

---

## Design System

The site uses a nature-inspired color palette:

| Variable | Value | Usage |
|----------|-------|-------|
| `--color-ivory` | `#f8f5ef` | Main background |
| `--color-beige` | `#ede8df` | Section backgrounds |
| `--color-terracotta` | `#b5614a` | Accents, labels, links |
| `--color-brown` | `#3d2e22` | Primary buttons, headings |
| `--color-forest` | `#2d3d25` | Philosophy section bg |
| `--color-olive` | `#6b7c4f` | Available status |

**Fonts:**
- **Cormorant Garamond** — headings, quotes, logo (serif)
- **Inter** — body text, labels, UI (sans-serif)

---

## License

Private project — Meadow Shore. All rights reserved.
