import axios from "axios";
import { useAuthStore } from "@/stores/authStore";

// Base URL of the backend API. Points at the deployed Cloud Run service in
// production (VITE_API_URL); falls back to the dev proxy path "/api/v1".
export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

// Attach the current JWT (from the Zustand auth store) to every request.
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
