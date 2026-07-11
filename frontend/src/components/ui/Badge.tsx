import { cn } from "@/lib/utils";

type Tone = "gray" | "blue" | "green" | "amber" | "red" | "purple";

const TONES: Record<Tone, string> = {
  gray: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  blue: "bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300",
  green: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
  amber: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  red: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  purple: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
};

export function Badge({
  children,
  tone = "gray",
  className,
}: {
  children: React.ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

const STATUS_TONES: Record<string, Tone> = {
  completed: "green",
  running: "blue",
  queued: "amber",
  pending: "amber",
  draft: "gray",
  failed: "red",
  cancelled: "gray",
  production: "green",
  staging: "amber",
  archived: "gray",
  none: "gray",
};

/** Coloured badge for a lifecycle status string. */
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONES[status] ?? "gray"}>{status}</Badge>;
}
