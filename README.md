# RP_Planner_373
we are developing a AI system that help diabetes patients

## Frontend

A simple Next.js App Router frontend using JavaScript and plain CSS.

### Run locally

Install dependencies once:

```sh
npm install
```

Start development:

```sh
npm run dev
```

Open http://localhost:3000.

For a production build, run `npm run build`, then `npm start`.

### Pages

- `/login`: email/password demo login.
- `/home`: DCare AI landing page with links to DFU, Retinopathy, and Member 1-3 sections.
- `/dfu`: dated wound-image visit workflow with local preview, visit history, and placeholders for future model results.
- `/retino`: Retinopathy research area.
- `/members/1` through `/members/3`: member work areas.

Edit the page components under `app/(workspace)/` to add module content. The shared page header and logout action are in `components/workspace-shell.jsx`.

### Demo login

Use any valid email and a non-empty password. This is a frontend prototype: it does not verify accounts or provide secure authentication. Only the email is kept in the current browser tab's session; passwords are not stored. Logout clears the demo session.

No patient dataset or trained model is connected. Add real server authentication and access controls before connecting patient data.

The DFU page keeps selected images and case IDs in memory only. They disappear on refresh and are not sent to a server. The classification image, healing date, and wound-area change graph remain empty until validated analysis is connected. The first dated image is a baseline; later comparisons are intended to use the previous visit.

The setup follows the official [Next.js installation documentation](https://nextjs.org/docs/app/getting-started/installation).
