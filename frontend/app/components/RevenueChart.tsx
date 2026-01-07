import { Box, Text, SkeletonDisplayText } from "@shopify/polaris";
import { useRevenueChart } from "../services/api";

export function RevenueChart() {
  const { data, isLoading, error } = useRevenueChart();

  if (isLoading) {
    return (
      <Box minHeight="200px" padding="400">
        <SkeletonDisplayText size="small" />
      </Box>
    );
  }

  if (error) {
    return (
      <Box minHeight="200px" padding="400">
        <Text as="p" tone="critical">
          Failed to load chart data
        </Text>
      </Box>
    );
  }

  const chartData = data?.data ?? [];

  // Simple bar chart using CSS
  const maxRevenue = Math.max(...chartData.map((d) => d.revenue), 1);

  return (
    <Box minHeight="200px">
      <div style={{ display: "flex", alignItems: "flex-end", gap: "4px", height: "180px" }}>
        {chartData.map((point, index) => {
          const height = (point.revenue / maxRevenue) * 100;
          return (
            <div
              key={index}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: `${height}%`,
                  minHeight: "4px",
                  backgroundColor: "var(--p-color-bg-fill-brand)",
                  borderRadius: "4px 4px 0 0",
                  transition: "height 0.3s ease",
                }}
                title={`$${point.revenue.toLocaleString()} - ${point.orders} orders`}
              />
              <Text as="span" variant="bodySm" tone="subdued">
                {new Date(point.date).toLocaleDateString(undefined, {
                  weekday: "short",
                })}
              </Text>
            </div>
          );
        })}
      </div>

      <Box paddingBlockStart="400">
        <Text as="p" variant="bodySm" tone="subdued" alignment="center">
          Total: ${data?.totalRevenue?.toLocaleString() ?? 0} from{" "}
          {data?.totalOrders ?? 0} orders
        </Text>
      </Box>
    </Box>
  );
}
