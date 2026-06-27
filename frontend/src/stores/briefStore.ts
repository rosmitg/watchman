import { create } from "zustand";
import { AxiosError } from "axios";
import { api } from "@/lib/api";
import type { Brief } from "@/types";

// All requests go through the shared axios instance in "@/lib/api", whose
// baseURL is import.meta.env.VITE_API_URL with a fallback of "/api/v1".

interface BriefState {
  brief: Brief | null;
  isLoading: boolean;
  isSyncing: boolean;
  isGenerating: boolean;
  error: string | null;
  syncPortfolio: () => Promise<void>;
  fetchTodayBrief: () => Promise<void>;
  generateBrief: () => Promise<void>;
  clearBrief: () => void;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof AxiosError
    ? err.response?.data?.detail ?? err.message
    : fallback;
}

export const useBriefStore = create<BriefState>((set) => ({
  brief: null,
  isLoading: false,
  isSyncing: false,
  isGenerating: false,
  error: null,

  // Pull the latest holdings from Alpaca so the brief reflects current
  // positions. Failures are surfaced but non-fatal — the caller still loads
  // whatever brief exists.
  syncPortfolio: async () => {
    set({ isSyncing: true, error: null });
    try {
      await api.post("/portfolio/sync");
      set({ isSyncing: false });
    } catch (err) {
      set({ error: errorMessage(err, "Failed to sync holdings"), isSyncing: false });
    }
  },

  fetchTodayBrief: async () => {
    set({ isLoading: true, error: null });
    try {
      const { data } = await api.get<Brief>("/brief/today");
      set({ brief: data, isLoading: false });
    } catch (err) {
      set({ error: errorMessage(err, "Failed to load today's brief"), isLoading: false });
    }
  },

  generateBrief: async () => {
    set({ isGenerating: true, error: null });
    try {
      const { data } = await api.post<Brief>("/brief/generate");
      set({ brief: data, isGenerating: false });
    } catch (err) {
      set({ error: errorMessage(err, "Failed to generate brief"), isGenerating: false });
    }
  },

  clearBrief: () => set({ brief: null, error: null }),
}));
