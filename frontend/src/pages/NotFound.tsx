import { Link } from "react-router-dom";

/** 404 fallback route. */
export function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
      <p className="text-6xl font-bold text-brand-600">404</p>
      <p className="text-slate-500">This page could not be found.</p>
      <Link to="/" className="btn-primary">
        Back to dashboard
      </Link>
    </div>
  );
}
