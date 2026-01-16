import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { DashboardStats, PaginatedInsights, RevenueChartData, Insight } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Get shop ID from session or context
function getShopId(): string {
  // In production, this would come from Shopify App Bridge or session
  // Guard against SSR - sessionStorage only exists in browser
  if (typeof window === "undefined") {
    return "demo-shop-id";
  }
  return sessionStorage.getItem("shop_id") || "demo-shop-id";
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}/api${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }

  return response.json();
}

// Dashboard Stats
export function useDashboardStats() {
  const shopId = getShopId();

  return useQuery({
    queryKey: ["dashboard", "stats", shopId],
    queryFn: () =>
      fetchApi<DashboardStats>(`/dashboard/stats?shop_id=${shopId}`),
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

// Revenue Chart
export function useRevenueChart(period = "7d") {
  const shopId = getShopId();

  return useQuery({
    queryKey: ["dashboard", "revenue-chart", shopId, period],
    queryFn: () =>
      fetchApi<RevenueChartData>(
        `/dashboard/revenue-chart?shop_id=${shopId}&period=${period}`
      ),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Insights
export function useInsights(page = 1, pageSize = 10) {
  const shopId = getShopId();

  return useQuery({
    queryKey: ["insights", shopId, page, pageSize],
    queryFn: () =>
      fetchApi<PaginatedInsights>(
        `/insights?shop_id=${shopId}&page=${page}&page_size=${pageSize}`
      ),
    staleTime: 60 * 1000,
  });
}

export function useDismissInsight() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (insightId: string) =>
      fetchApi<{ id: string; message: string }>(
        `/insights/${insightId}/dismiss`,
        { method: "POST" }
      ),
    onSuccess: () => {
      // Invalidate insights queries to refetch
      queryClient.invalidateQueries({ queryKey: ["insights"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "stats"] });
    },
  });
}

// Dashboard Summary (single call for all data)
export function useDashboardSummary() {
  const shopId = getShopId();

  return useQuery({
    queryKey: ["dashboard", "summary", shopId],
    queryFn: () =>
      fetchApi<{
        stats: DashboardStats;
        revenueChart: RevenueChartData;
        topProducts: Array<{
          id: string;
          title: string;
          revenue: number;
          unitsSold: number;
        }>;
        activeInsightsCount: number;
      }>(`/dashboard/summary?shop_id=${shopId}`),
    staleTime: 60 * 1000,
  });
}
