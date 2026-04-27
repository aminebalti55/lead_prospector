import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "./client";

export function useStats() {
  return useQuery({ queryKey: ["stats"], queryFn: () => apiFetch<any>("/stats") });
}

export function useColdStats() {
  return useQuery({ queryKey: ["stats", "cold"], queryFn: () => apiFetch<any>("/stats/cold") });
}

export function useDirectStats() {
  return useQuery({ queryKey: ["stats", "direct"], queryFn: () => apiFetch<any>("/stats/direct") });
}

export function useEmailTemplates() {
  return useQuery({ queryKey: ["email", "templates"], queryFn: () => apiFetch<any>("/email/templates") });
}

export function useSendEmail() {
  return useMutation({ mutationFn: (data: any) => apiFetch("/email/send", { method: "POST", body: JSON.stringify(data) }) });
}

export function useBatchEmail() {
  return useMutation({ mutationFn: (data: any) => apiFetch<any>("/email/batch", { method: "POST", body: JSON.stringify(data) }) });
}

export function usePreviewEmail() {
  return useMutation({ mutationFn: (data: any) => apiFetch<any>("/email/preview", { method: "POST", body: JSON.stringify(data) }) });
}
