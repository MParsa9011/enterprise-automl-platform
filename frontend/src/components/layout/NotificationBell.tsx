import { Bell } from "lucide-react";
import { useState } from "react";

import { Spinner } from "@/components/ui/Spinner";
import {
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from "@/hooks/useNotifications";
import { formatDate } from "@/lib/utils";

/** Topbar notification dropdown with an unread-count indicator. */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { data: unread } = useUnreadCount();
  const { data, isLoading } = useNotifications(1, 8);
  const markRead = useMarkNotificationRead();

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        aria-label="Notifications"
        className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
      >
        <Bell className="h-5 w-5" />
        {unread ? (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="card animate-fade-in absolute right-0 z-20 mt-2 w-80 overflow-hidden">
            <div className="border-b border-slate-200 px-4 py-3 text-sm font-semibold dark:border-slate-800">
              Notifications
            </div>
            <div className="max-h-96 overflow-y-auto">
              {isLoading && (
                <div className="flex justify-center py-6">
                  <Spinner />
                </div>
              )}
              {data?.items.length === 0 && (
                <p className="px-4 py-6 text-center text-sm text-slate-500">No notifications</p>
              )}
              {data?.items.map((notification) => (
                <button
                  key={notification.id}
                  onClick={() => markRead.mutate(notification.id)}
                  className={`block w-full border-b border-slate-100 px-4 py-3 text-left last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50 ${
                    notification.read_at ? "opacity-60" : ""
                  }`}
                >
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {notification.title}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">{notification.message}</p>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {formatDate(notification.created_at)}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
