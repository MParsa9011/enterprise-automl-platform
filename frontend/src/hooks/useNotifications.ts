import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Notification, Page } from "@/types/api";

export function useNotifications(page = 1, size = 20) {
  return useQuery({
    queryKey: ["notifications", page, size],
    queryFn: async () => {
      const { data } = await api.get<Page<Notification>>("/notifications", {
        params: { page, size },
      });
      return data;
    },
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => {
      const { data } = await api.get<{ unread: number }>("/notifications/unread-count");
      return data.unread;
    },
    refetchInterval: 30_000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/notifications/${id}/read`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });
}
