# Frontend

The frontend is a **Vite + React 18 + TypeScript** single-page admin dashboard,
styled with **TailwindCSS** and driven by **TanStack Query**.

## Stack

| Concern | Choice |
|---------|--------|
| Build / dev | Vite 6 |
| UI | React 18, TypeScript (strict) |
| Styling | TailwindCSS (class-based dark mode) |
| Data fetching | TanStack Query (React Query) |
| Routing | React Router 6 |
| Forms | React Hook Form |
| HTTP | Axios (with a refresh-token interceptor) |
| Icons | lucide-react |
| Tests | Vitest + Testing Library |

## Structure

```
src/
  lib/          api client (axios + refresh interceptor), token store, query client, utils
  context/      auth context + provider
  hooks/        TanStack Query data hooks (projects, datasets, experiments, models, notifications)
  components/
    ui/         primitives (Card, Badge, Modal, Spinner, StateViews, PageHeader)
    layout/     AppShell, Sidebar, Topbar, ThemeToggle, NotificationBell
  pages/        Login, Register, Dashboard, Projects, Datasets, Experiments, Models
  App.tsx       route table
  main.tsx      providers (QueryClient, Router, AuthProvider)
```

## Authentication flow

- `lib/tokenStore.ts` persists the JWT pair in `localStorage` and notifies
  subscribers on change.
- `lib/api.ts` attaches the access token to every request and, on a `401`,
  **transparently refreshes** the token once (de-duplicating concurrent refreshes)
  and replays the request; a failed refresh clears the session.
- `context/AuthProvider.tsx` restores the session on load and exposes
  `login` / `register` / `logout` via the `useAuth` hook.
- `ProtectedRoute` gates authenticated routes.

## Dev server & API proxy

The Vite dev server proxies `/api` to the backend (default `http://localhost:8000`,
overridable via `VITE_API_PROXY_TARGET` in `frontend/.env`), so the browser talks
to a single origin — matching the production Nginx reverse proxy.

## Theming

Dark mode toggles the `dark` class on `<html>` and persists the choice; an inline
script in `index.html` applies the stored/OS theme before first paint to avoid a
flash. UI is styled for both light and dark.

## Scripts

```bash
npm run dev        # dev server (http://localhost:5173)
npm run build      # tsc --noEmit && vite build
npm run typecheck  # tsc --noEmit
npm run lint       # eslint --max-warnings 0
npm run test       # vitest
```
