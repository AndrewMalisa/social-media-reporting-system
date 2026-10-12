# Social Media Reporting System

## Windows setup

1. Install Python 3.12 or 3.13.
2. Open Command Prompt inside this folder.
3. Run `py -m venv .venv` then `.venv\Scripts\activate`.
4. Run `python -m pip install -r requirements.txt`.
5. Copy `.env.example` to `.env` and replace APP_PASSWORD and SESSION_SECRET with strong values. Generate a session secret using `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
6. Run `python -m uvicorn app:app --host 127.0.0.1 --port 8000`.
7. Visit http://127.0.0.1:8000 and sign in.

## Features

Private login, four social platforms, post URL validation, manual data entry, KPI summaries, date/platform/search filters, CSV export, delete posts. Engagement rate = (likes + comments + shares) / reach x 100. Ad spend is entered in TZS.

## Auto-fetch limitations

This version DOES NOT automatically fetch metrics. URL validation only identifies the platform. APIs and provider credentials will be needed for any automated fetching. Public post URLs alone do not generally reveal private reach, followers gained, or ad spend. Do not enter platform passwords into this app.

## Hosting

`render.yaml` is included. Add secure environment variables when deploying. Render free service storage is ephemeral, so SQLite records may disappear on redeploy or restart. Use a persistent PostgreSQL database or paid persistent disk for production. For initial tests, export CSV frequently.

## Security

Keep `.env` private. Use HTTPS and COOKIE_SECURE=true when hosted. This starter supports one administrator; add proper multi-user authentication, CSRF protections, rate limits, and backups before wider deployment.
