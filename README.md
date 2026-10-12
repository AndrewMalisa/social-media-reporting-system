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

## Deploy to Vercel

1. Create a PostgreSQL database in [Neon](https://neon.tech/) and copy its pooled connection string.
2. In [Vercel](https://vercel.com/new), import this GitHub repository. Vercel detects the FastAPI app automatically.
3. Add these environment variables to the Vercel project for Production (and Preview if needed):
   - `DATABASE_URL`: the Neon connection string.
   - `APP_USERNAME`: your administrator username.
   - `APP_PASSWORD`: a strong, unique password.
   - `SESSION_SECRET`: generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   - `COOKIE_SECURE`: `true`.
4. Deploy the project. Vercel will create the posts table in PostgreSQL on startup.

Do not upload `.env` or put credentials in source control. Vercel deployments use PostgreSQL when `DATABASE_URL` is set; local development continues to use `reports.db` by default. Existing local SQLite records are not copied to Neon automatically. `render.yaml` is also included for Render deployment.

## Hosting notes

Vercel runs this FastAPI app as a serverless function. Use PostgreSQL for persistent records; the local SQLite database is only for development and is not suitable for Vercel's ephemeral filesystem.

## Security

Keep `.env` private. Use HTTPS and COOKIE_SECURE=true when hosted. This starter supports one administrator; add proper multi-user authentication, CSRF protections, rate limits, and backups before wider deployment.
