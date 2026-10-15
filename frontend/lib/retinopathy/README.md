# Retinopathy integration

The live UI uses authenticated FastAPI requests. See `../../RETINOPATHY_FRONTEND_INTEGRATION.md` for contracts, commands, verification, and blockers.

`mockData.js` is retained only as a legacy demonstration fixture; no runtime component imports it. Live results come from `api.js` and are validated/adapted by `contract.js`. Numeric probabilities remain fractions internally; `constants.js` formats percentages for display.
