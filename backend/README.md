# DiaCare AI Backend

FastAPI starter structure for the four research components: diabetes, retinopathy,
wound healing, and diet planning. Component routers are registered under `/api`;
prediction endpoints, trained models, and database integration are not implemented yet.

## Run locally

From the project root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Health check: http://127.0.0.1:8000/health
API documentation: http://127.0.0.1:8000/docs

## Member work areas

Each member owns their component files in `app/api`, `app/services`, `app/models`,
`app/schemas`, and `app/database/repositories`. Store saved models in the matching
`trained_models` folder. Share reusable processing code in `app/utils`.

Keep local configuration in `.env` and document variable names in `.env.example`.
Uploaded files, generated outputs, and model artifacts are excluded from Git;
`.gitkeep` files preserve the folder structure.

## Account storage

Authentication loads `backend/.env`. Set `MONGODB_URI` and `MONGODB_DATABASE`
to use MongoDB; connection failures return HTTP 503 and never silently discard accounts.
Without `MONGODB_URI`, local development uses persistent SQLite in
`backend/outputs/auth.sqlite3` (excluded from Git). Accounts created by the old
in-memory fallback cannot be recovered after a restart and must be registered again.
Logout removes the browser session, not the saved account. Set a strong
`JWT_SECRET` before deploying.

## Component demo accounts

For development only, run `python -m scripts.seed_demo_accounts` from `backend`
to create diabetes@diabeticcare.com, retinopathy@diabeticcare.com,
wound@diabeticcare.com, and diet@diabeticcare.com, each with password `2026!`.
Existing accounts are not overwritten. Each signs in through `/login` and opens
its component dashboard. These are test identifiers, not verified email inboxes.
New public registrations still require the stronger password policy.
