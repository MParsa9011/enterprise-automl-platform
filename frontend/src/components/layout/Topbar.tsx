import { LogOut, Menu } from "lucide-react";

import { NotificationBell } from "@/components/layout/NotificationBell";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { useAuth } from "@/hooks/useAuth";

/** Top navigation bar with theme toggle, notifications and user menu. */
export function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { user, logout } = useAuth();
  const initials = (user?.full_name ?? user?.email ?? "?")
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/80 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
      <button className="lg:hidden" onClick={onMenuClick} aria-label="Open menu">
        <Menu className="h-6 w-6 text-slate-600 dark:text-slate-300" />
      </button>
      <div className="flex flex-1 items-center justify-end gap-2">
        <ThemeToggle />
        <NotificationBell />
        <div className="ml-2 flex items-center gap-3 border-l border-slate-200 pl-3 dark:border-slate-800">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
            {initials}
          </div>
          <div className="hidden text-sm sm:block">
            <p className="font-medium text-slate-800 dark:text-slate-100">
              {user?.full_name ?? user?.email}
            </p>
            <p className="text-xs text-slate-500">{user?.roles.map((r) => r.name).join(", ")}</p>
          </div>
          <button
            onClick={() => void logout()}
            aria-label="Log out"
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-red-600 dark:hover:bg-slate-800"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
