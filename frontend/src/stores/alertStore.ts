import { create } from "zustand";
import type { Alert } from "@/types";

interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  addAlert: (alert: Alert) => void;
  markAllRead: () => void;
  connectWebSocket: (token: string) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  unreadCount: 0,

  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts],
      unreadCount: alert.read ? state.unreadCount : state.unreadCount + 1,
    })),

  markAllRead: () =>
    set((state) => ({
      alerts: state.alerts.map((a) => ({ ...a, read: true })),
      unreadCount: 0,
    })),

  connectWebSocket: (_token: string) => {
    // Real-time alert delivery is wired up in Sprint 3.
    console.log("WebSocket connection pending Sprint 3");
  },
}));
