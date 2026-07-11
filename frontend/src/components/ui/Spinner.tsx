import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

/** Indeterminate loading spinner. */
export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-5 w-5 animate-spin text-brand-500", className)} />;
}
