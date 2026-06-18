import { create } from "zustand";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  setUser: (user: User | null, token: string | null) => void;
  clearUser: () => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: true,

  setUser: (user, token) => set({ user, token }),

  clearUser: () => set({ user: null, token: null }),

  initialize: async () => {
    const applySession = (session: Session | null) =>
      set({
        user: session?.user ?? null,
        token: session?.access_token ?? null,
      });

    const {
      data: { session },
    } = await supabase.auth.getSession();
    applySession(session);
    set({ isLoading: false });

    supabase.auth.onAuthStateChange((_event, session) => {
      applySession(session);
    });
  },
}));
