import {
  BlockStack,
  InlineStack,
  Text,
  Button,
  Badge,
  Box,
  SkeletonBodyText,
} from "@shopify/polaris";
import { useInsights, useDismissInsight } from "../services/api";
import type { Insight } from "../types";

const severityTones: Record<string, "critical" | "warning" | "attention" | "info"> = {
  critical: "critical",
  high: "warning",
  medium: "attention",
  low: "info",
};

function InsightCard({ insight }: { insight: Insight }) {
  const dismissMutation = useDismissInsight();

  const handleDismiss = () => {
    dismissMutation.mutate(insight.id);
  };

  return (
    <Box
      padding="300"
      borderRadius="200"
      background="bg-surface-secondary"
    >
      <BlockStack gap="200">
        <InlineStack align="space-between">
          <Badge tone={severityTones[insight.severity] ?? "info"}>
            {insight.severity.toUpperCase()}
          </Badge>
          <Text as="span" variant="bodySm" tone="subdued">
            {insight.type.replace(/_/g, " ")}
          </Text>
        </InlineStack>

        <Text as="p" variant="bodyMd" fontWeight="semibold">
          {insight.title}
        </Text>

        <Text as="p" variant="bodySm" tone="subdued">
          {insight.actionSummary}
        </Text>

        {insight.expectedUplift && (
          <Text as="p" variant="bodySm" tone="success">
            Expected: {insight.expectedUplift}
          </Text>
        )}

        <InlineStack gap="200">
          {insight.adminDeepLink && (
            <Button
              size="slim"
              url={`https://admin.shopify.com${insight.adminDeepLink}`}
              target="_blank"
            >
              View in Shopify
            </Button>
          )}
          <Button
            size="slim"
            variant="plain"
            onClick={handleDismiss}
            loading={dismissMutation.isPending}
          >
            Dismiss
          </Button>
        </InlineStack>
      </BlockStack>
    </Box>
  );
}

export function InsightsList() {
  const { data, isLoading, error } = useInsights();

  if (isLoading) {
    return (
      <BlockStack gap="300">
        {[1, 2, 3].map((i) => (
          <Box key={i} padding="300" background="bg-surface-secondary" borderRadius="200">
            <SkeletonBodyText lines={3} />
          </Box>
        ))}
      </BlockStack>
    );
  }

  if (error) {
    return (
      <Text as="p" tone="critical">
        Failed to load insights
      </Text>
    );
  }

  const insights = data?.items ?? [];

  if (insights.length === 0) {
    return (
      <Box padding="400" background="bg-surface-secondary" borderRadius="200">
        <Text as="p" alignment="center" tone="subdued">
          No active insights. Your store is running smoothly!
        </Text>
      </Box>
    );
  }

  return (
    <BlockStack gap="300">
      {insights.map((insight) => (
        <InsightCard key={insight.id} insight={insight} />
      ))}
    </BlockStack>
  );
}
