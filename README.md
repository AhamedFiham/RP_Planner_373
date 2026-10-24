# RP_Planner_373

Full-stack project for an AI system that helps diabetes patients.

## Project structure

- `frontend/` — Next.js application
- `backend/` — API server and database integration

## Run the frontend

```sh
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:3000.

## Wound clinic workflow

The wound workspace at `/dashboard/wound` (also available at `/dfu`) now supports
separate patients, multiple wounds per patient, and persistent dated visit images.
Run the backend as described in `backend/README.md`; install its updated
requirements and restart it after pulling this change.

The wound and tissue panels support the three supplied segmentation architectures
through a separate PyTorch runtime. A color-coded line chart shows tissue
proportions across visits using the same model and one selected photo per visit.
Healing percentage and outcome assessment await the comparison method. The
workflow accepts images only.

See [the implementation plan](docs/wound-clinic-implementation.md) for completed
steps, local setup, and validation. Chart calculations can be checked from the
project root with `node --test frontend/tests/wound-trends.test.mjs`.
