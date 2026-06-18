import { create } from "zustand";
import { AxiosError } from "axios";
import { api } from "@/lib/api";
import type { Brief } from "@/types";

interface BriefState {
  brief: Brief | null;
  isLoading: boolean;
  error: string | null;
  fetchTodayBrief: () => Promise<void>;
  clearBrief: () => void;
}

export const useBriefStore = create<BriefState>((set) => ({
  brief: null,
  isLoading: false,
  error: null,

  fetchTodayBrief: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await api.get<Brief>("/brief/today");
      set({ brief: data, isLoading: false });
    } catch (err) {
      const message =
        err instanceof AxiosError
          ? err.response?.data?.detail ?? err.message
          : "Failed to load today's brief";
      set({ error: message, isLoading: false });
    }
  },

  clearBrief: () => set({ brief: null, error: null }),
}));
