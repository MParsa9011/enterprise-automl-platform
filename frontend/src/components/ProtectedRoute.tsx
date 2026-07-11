import { Navigate, useLocation } from "react-router-dom";

import { LoadingState } from "@/components/ui/StateViews";
import { useAuth } from "@/hooks/useAuth";

/** Gate for authenticated routes; redirects to login when unauthenticated. */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingState label="Restoring session…" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
