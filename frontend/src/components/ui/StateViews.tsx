import { AlertCircle, Inbox } from "lucide-react";

import { Spinner } from "@/components/ui/Spinner";

/** Centered loading indicator for query-loading states. */
export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-500">
      <Spinner className="h-6 w-6" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

/** Error panel with an optional retry action. */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <AlertCircle className="h-8 w-8 text-red-500" />
      <p className="max-w-md text-sm text-slate-600 dark:text-slate-400">{message}</p>
      {onRetry && (
        <button className="btn-secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

/** Empty-collection placeholder. */
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <Inbox className="h-8 w-8 text-slate-400" />
      <p className="font-medium text-slate-700 dark:text-slate-200">{title}</p>
      {description && (
        <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
