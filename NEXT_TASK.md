# Next Task

## ▶ M8 — Frontend Admin Dashboard

**Goal:** A modern, responsive React + TypeScript admin dashboard for the
platform, wired to the v1 API with authenticated data fetching, dark mode and
proper loading/error states.

### Stack
Vite + React 18 + TypeScript + TailwindCSS + TanStack Query + React Router +
React Hook Form + Axios + Recharts (for Plotly-free chart rendering of summary
data; raw Plotly figure JSON from the API can be embedded where needed).

### Scope (delivered as vertical slices)
1. **Tooling & scaffold** — Vite project, Tailwind, ESLint/Prettier, tsconfig,
   env config, path aliases.
2. **API layer** — typed Axios client with access-token attach + refresh-token
   rotation interceptor; generated-style TS types mirroring the DTOs.
3. **Auth** — login/register pages, auth context, protected routes, token store.
4. **App shell** — responsive sidebar + topbar, dark-mode toggle (persisted),
   notification bell (unread count), user menu.
5. **Pages** — Dashboard (KPIs), Projects (list/create), Datasets (upload +
   statistics), Experiments (create + runs + metrics/figures), Model registry
   (list/deploy/compare + predict form).
6. **UX** — TanStack Query loading/error/empty states, toasts, skeletons.
7. **Quality** — TypeScript strict, ESLint clean; a couple of component tests.

### Definition of done
- `npm run dev` serves the dashboard; `npm run build` succeeds; `tsc` clean.
- Auth flow works against the API; core pages render live data.
- Atomic Conventional Commits; `PROJECT_STATUS.md` + this file updated.
