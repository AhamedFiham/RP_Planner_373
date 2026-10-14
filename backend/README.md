# Backend

This directory is reserved for backend services, separate from the Next.js frontend in `frontend/`.

No API, FastAPI application, or model integration is currently implemented. Add backend-specific dependencies, configuration, and run instructions here when backend development begins.

Store original datasets in `datasets/<component>/raw/` and cleaned datasets in
`datasets/<component>/processed/`, where `<component>` is `diabetes`,
`retinopathy`, `wound`, or `diet`. Dataset files are excluded from Git; `.gitkeep`
files preserve these folders. Saved trained models belong in `trained_models/`.
