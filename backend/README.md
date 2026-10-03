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
