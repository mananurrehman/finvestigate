# 🔍 Finvestigate

> Investigate your finances. Track smarter. Spend wiser.

Finvestigate is a multi-user personal finance tracker built with **Python + Flask** and **PostgreSQL**. Users sign up, log transactions (income/expense), browse and filter their transaction history, and see a monthly dashboard with a category-wise spending breakdown chart.

> **Note on this README:** The repository's original README only described the project as "planned" / "under active development" with a TBD database and frontend. That's outdated — the codebase is significantly further along than the README suggests. This document reflects what is **actually implemented in code**, not the aspirational feature list.

---

## Table of Contents

- [What This App Actually Is](#what-this-app-actually-is)
- [Tech Stack](#tech-stack)
- [Data Model](#data-model)
- [Project Structure](#project-structure)
- [Routes / Endpoints](#routes--endpoints)
- [Getting Started (Local Dev)](#getting-started-local-dev)
- [Environment Variables](#environment-variables)
- [Running with Docker](#running-with-docker)
- [Database Seeding](#database-seeding)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Deployment](#deployment)
- [Known Gaps / Things to Improve](#known-gaps--things-to-improve)
- [Color Scheme](#color-scheme)
- [License](#license)

---

## What This App Actually Is

A server-rendered Flask web app (not an API-only backend, not a SPA) where each authenticated user manages their **own private set of financial data**:

- **Auth**: email/password signup & login, hashed passwords, session-based auth via Flask-Login
- **Role-based access control**: every user has a role (`admin` or `user`) via a `roles` table
- **Transactions**: create, edit, delete income/expense entries with a title, amount, category, date, and optional note
- **Transaction browsing**: paginated list (10/page), filterable by type/category/month, searchable by title/note
- **Dashboard**: current month's income, expenses, balance, 5 most recent transactions, and a donut chart (Chart.js) of expenses by category
- **Categories**: system-seeded defaults (5 income, 7 expense — see [Database Seeding](#database-seeding)), each with an emoji icon
- **Budgets** *(data model exists, UI/routes not yet built — see [Known Gaps](#known-gaps--things-to-improve))*: monthly budget per category with an alert threshold
- **Audit log** *(data model exists, not yet wired into routes)*: intended to track user actions with IP/module
- **Multi-currency preference** per user (defaults to `PKR`), stored but not yet used for conversion — it's a display label only
- Static pages: Home, About, How to Use, Contact
- Custom error pages: 403, 404, 500

In short: it's a **CRUD-heavy personal finance tracker**, further along than a starter template, but with a few modeled features (budgets, audit logging, real currency conversion) not yet exposed through routes/UI.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| Web framework | Flask 3.1.3 | Blueprint-based (`main`, `auth`) |
| ORM | SQLAlchemy 2.0 (via Flask-SQLAlchemy 3.1.1) | |
| Database | PostgreSQL 15 | via `psycopg2-binary` |
| Migrations | Flask-Migrate 4.1.0 (Alembic) | |
| Auth | Flask-Login 0.6.3 | session-based |
| Password hashing | Werkzeug security helpers | `generate_password_hash` / `check_password_hash` |
| Email | Flask-Mail 0.10.0 | configured but not yet used in any route |
| Frontend templating | Jinja2 | server-rendered HTML |
| CSS | Tailwind CSS | **loaded via CDN** (`cdn.tailwindcss.com`), not a build pipeline |
| Charts | Chart.js | loaded via CDN, donut chart on dashboard |
| Config/env | python-dotenv | `.env` / `.env.production` |
| Testing | pytest | `tests/test_routes.py` |
| Containerization | Docker (multi-stage build), Docker Compose | non-root user, healthcheck |
| CI | GitHub Actions — `ci-pipeline.yml` | flake8 lint, bandit security scan |
| CD | GitHub Actions — `cd-pipeline.yml` (triggered via `workflow_run` after CI) | hadolint (Dockerfile lint), pip-audit (dependency scan) |
| Alt. deploy path | Azure Pipelines (`azure-pipelines-deploy.yml`, `azure-pipelines-teardown.yml`) | separate/parallel deploy option |
| Secret scanning | Gitleaks (`.gitleaks.toml`) | |

---

## Data Model

Six tables, defined in `app/models.py`:

```
Role (roles)
 └─ id, name [admin|user], description, created_at

User (users)
 └─ id, full_name, username (unique), email (unique), password (hashed),
    is_active, is_verified, currency_preference (default "PKR"),
    role_id → roles.id, created_at, updated_at, last_login

Category (categories)
 └─ id, name, type [income|expense], icon (emoji), is_default,
    user_id → users.id (nullable — null = system default category)

Transaction (transactions)
 └─ id, title, amount (Numeric 12,2), type [income|expense], note, date,
    user_id → users.id, category_id → categories.id, created_at, updated_at

Budget (budgets)
 └─ id, title, amount (Numeric 12,2), month, year, alert_at (default 80),
    user_id → users.id, category_id → categories.id, created_at

AuditLog (audit_logs)
 └─ id, action, module, ip_address, user_id → users.id, created_at
```

Relationships: a `User` has many `Transaction`, `Budget`, and `AuditLog` rows (cascade delete). A `Transaction` and `Budget` optionally belong to a `Category`.

---

## Project Structure

```
finvestigate/
├── .github/workflows/
│   ├── ci-pipeline.yml         # lint (flake8) + security scan (bandit)
│   └── cd-pipeline.yml         # runs after CI: hadolint + pip-audit
├── app/
│   ├── __init__.py             # app factory, extension init, auto-seeding, error handlers
│   ├── auth.py                 # signup/login/logout blueprint
│   ├── config.py               # Config / DevelopmentConfig / ProductionConfig / TestingConfig
│   ├── models.py                # SQLAlchemy models (6 tables, see above)
│   ├── routes.py                # main blueprint: dashboard, transactions CRUD, static pages
│   ├── seed.py                   # standalone seed script (roles + default categories)
│   └── templates/
│       ├── base.html            # layout, Tailwind CDN, nav
│       ├── home.html, about.html, contact.html, how_to_use.html
│       ├── dashboard.html        # summary cards + Chart.js donut chart
│       ├── transactions.html     # paginated/filterable transaction table
│       ├── auth/login.html, auth/signup.html
│       └── errors/403.html, 404.html, 500.html
├── tests/
│   └── test_routes.py           # smoke tests: public routes 200, protected routes redirect (302)
├── azure-pipelines-deploy.yml
├── azure-pipelines-teardown.yml
├── Dockerfile                    # multi-stage: builder → slim production image
├── docker-compose.yml            # web (Flask) + db (Postgres 15-alpine)
├── deploy.sh                     # server-side deploy script (git pull + docker compose up), invoked via SSH from CI
├── entrypoint.sh                 # waits for DB, runs migrations, starts Flask
├── requirements.txt
├── run.py                        # entrypoint: creates app via factory, runs dev server
└── .gitleaks.toml                # secret-scanning config
```

---

## Routes / Endpoints

**Public**
| Method | Path | Description |
|---|---|---|
| GET | `/` | Home page |
| GET | `/about` | About page |
| GET | `/how-to-use` | How-to-use page |
| GET | `/contact` | Contact page |
| GET, POST | `/signup` | Create account |
| GET, POST | `/login` | Log in |
| POST | `/logout` | Log out |

**Authenticated (require login)**
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard` | Monthly summary + recent transactions + category chart |
| GET | `/transactions` | Paginated, filterable, searchable transaction list |
| POST | `/dashboard/add-transaction` | Create a transaction |
| POST | `/transactions/edit/<id>` | Edit a transaction (owner-only, 404 otherwise) |
| POST | `/transactions/delete/<id>` | Delete a transaction (owner-only, 404 otherwise) |

> Budget and audit-log routes are **not yet implemented** despite the models existing.

---

## Getting Started (Local Dev)

### Prerequisites
- Python 3.11+
- PostgreSQL 15 (local install or Docker)
- pip / virtualenv

### Steps

```bash
# 1. Clone
git clone https://github.com/mananurrehman/finvestigate.git
cd finvestigate

# 2. Create & activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file from the provided example
cp .env.example .env
# then edit .env with your real values

# 5. Make sure PostgreSQL is running and the database from .env exists

# 6. Run the app (auto-creates tables + seeds roles/categories on first run)
python run.py
```

App will be available at `http://localhost:5000`.

---

## Environment Variables

See `.env.example` for the full list with comments. Summary:

```bash
# Flask
SECRET_KEY=change-me-in-production

# Database — either provide DATABASE_URL directly, or the individual parts below
DATABASE_URL=postgresql://user:password@localhost:5432/finvestigate
DB_USER=
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
DB_NAME=finvestigate

# Mail (Flask-Mail — configured, not yet used by any route)
MAIL_SERVER=
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=
```

> Note: `app/__init__.py` builds the DB URI from `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` directly and does **not** check `DATABASE_URL` first, while `app/config.py`'s `Config.get_db_uri()` *does* prefer `DATABASE_URL`. These two are inconsistent — `config.py`'s config classes aren't actually wired into `create_app()` at all right now. Set both `DATABASE_URL` and the individual `DB_*` vars in your `.env` to be safe until this is fixed (see [Known Gaps](#known-gaps--things-to-improve)).

---

## Running with Docker

```bash
# Build and run the full stack (Flask + Postgres) via Docker Compose
docker compose --env-file .env.production up --build
```

- `web` service exposes the app on host port `5002` → container port `5000`
- `db` service runs Postgres 15-alpine with a persistent volume bound to `/home/ubuntu/finvestigate-data/postgres` (this is a hardcoded path meant for the production server — override for local use)
- `entrypoint.sh` waits for the DB, runs migrations (or `db.create_all()` if no `migrations/` folder exists yet), then starts Flask

---

## Database Seeding

Seeding happens automatically **every time the app starts** (`seed_defaults()` in `app/__init__.py`), and is idempotent (checks `.count() == 0` first). There's also a standalone script for manual seeding:

```bash
python -m app.seed
```

Default roles: `admin`, `user`

Default income categories: Salary 💼, Freelance 💻, Investment 📈, Forex Trading 💹, Other Income 💰

Default expense categories: Food 🍔, Transport 🚗, Shopping 🛍️, Bills 📄, Health 🏥, Education 📚, Other 📦

---

## Testing

```bash
pytest
```

Current coverage (`tests/test_routes.py`) is minimal — smoke tests only:
- Public pages return `200`
- Protected routes (`/dashboard`, `/transactions`) redirect (`302`) when not logged in

No tests currently cover auth flows, transaction CRUD, filtering, or model validation.

---

## CI/CD

**CI (`ci-pipeline.yml`)** — triggers on push to `dev`:
- `flake8` lint (non-blocking — warnings logged, doesn't fail the build)
- `bandit` security scan

**CD (`cd-pipeline.yml`)** — triggers after CI completes successfully:
- `hadolint` — Dockerfile lint
- `pip-audit` — dependency vulnerability scan
- (presumably a deploy job calling `deploy.sh` over SSH, matching the script's comment "Called by GitHub Actions Workflow via SSH")

**Alternative pipeline:** `azure-pipelines-deploy.yml` / `azure-pipelines-teardown.yml` provide an Azure DevOps-based deploy/teardown path as an alternative to the GitHub Actions + SSH route.

---

## Deployment

The app is designed for a **self-managed VM**, not serverless:

1. `deploy.sh` runs on the target server (via SSH from CI): clones/pulls the repo, tears down old containers, rebuilds, and brings the stack up with `docker compose`
2. Persistent Postgres data is bound to a fixed host path (`/home/ubuntu/finvestigate-data/postgres`)
3. The Dockerfile is a **multi-stage build**: a `builder` stage installs dependencies, and the final slim image copies only the installed packages + app code, runs as a non-root `finvestigate` user, and defines a `HEALTHCHECK` hitting `/`

---

## Known Gaps / Things to Improve

This section is here deliberately — the repo isn't "perfect," and a new contributor should know where the rough edges are:

1. **README was stale** — described the app as feature-incomplete when the codebase is much further along (this file replaces that).
2. **No `.env.example` was previously committed** — this has been added alongside this README to fix that.
3. **Config duplication/inconsistency** — `app/config.py` defines `DevelopmentConfig`/`ProductionConfig`/`TestingConfig`, but `create_app()` in `app/__init__.py` builds its own config inline instead of using them. Pick one source of truth.
4. **Budgets model has no routes/UI** — schema exists (`Budget` table, `alert_at` threshold) but nothing in `routes.py` reads or writes it yet.
5. **Audit log model has no writers** — `AuditLog` table exists but no route currently creates a log entry.
6. **Flask-Mail is configured but unused** — no password-reset, email verification, or notification flow uses it yet, despite `is_verified` existing on the `User` model.
7. **`currency_preference` is cosmetic only** — no actual currency conversion; it's just a label.
8. **Tailwind via CDN** — fine for prototyping, but no purge/build step means larger payloads and no custom design tokens; a proper Tailwind build (PostCSS/CLI) would be more production-appropriate.
9. **Test coverage is minimal** — only smoke tests for route status codes; no coverage of business logic (transaction totals, filters, pagination, budget alerts).
10. **`flake8` in CI is non-blocking** (`|| true`) — lint issues are surfaced but never fail the build.
11. **Hardcoded deployment path** in `docker-compose.yml` (`/home/ubuntu/finvestigate-data/postgres`) — not portable to other environments without editing the compose file.

---

## Color Scheme

```
Primary:     #6366f1  (Indigo)
Secondary:   #8b5cf6  (Purple)
Accent:      #06b6d4  (Cyan)
Success:     #10b981  (Emerald)
Warning:     #f59e0b  (Amber)
Danger:      #ef4444  (Red)

Light Mode:
  Background: #f8fafc
  Surface:    #ffffff
  Text:       #1e293b
  Muted:      #64748b

Dark Mode:
  Background: #0f172a
  Surface:    #1e293b
  Text:       #f1f5f9
  Muted:      #94a3b8
```

---

## License

MIT License
