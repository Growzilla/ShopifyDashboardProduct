// API Response Types

export interface DashboardStats {
  yesterdayRevenue: number;
  weekAvgRevenue: number;
  yesterdayOrders: number;
  weekAvgOrders: number;
  yesterdayAov: number;
  weekAvgAov: number;
  revenueDelta: number;
  ordersDelta: number;
  aovDelta: number;
}

export interface RevenueDataPoint {
  date: string;
  revenue: number;
  orders: number;
  aov: number;
}

export interface RevenueChartData {
  data: RevenueDataPoint[];
  period: string;
  totalRevenue: number;
  totalOrders: number;
}

export interface Insight {
  id: string;
  shopId: string;
  type: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  actionSummary: string;
  expectedUplift: string | null;
  confidence: number;
  payload: Record<string, unknown>;
  adminDeepLink: string | null;
  createdAt: string;
  dismissedAt: string | null;
}

export interface PaginatedInsights {
  items: Insight[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface Shop {
  id: string;
  domain: string;
  scopes: string;
  deepModeEnabled: boolean;
  clarityProjectId: string | null;
  lastSyncAt: string | null;
  syncStatus: string;
  createdAt: string;
}

export interface TopProduct {
  id: string;
  title: string;
  revenue: number;
  unitsSold: number;
  imageUrl: string | null;
}
