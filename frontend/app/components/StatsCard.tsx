import { Card, Text, BlockStack, InlineStack, SkeletonBodyText, Icon } from "@shopify/polaris";
import type { IconSource } from "@shopify/polaris-icons";

interface StatsCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  comparison?: number;
  loading?: boolean;
  icon?: IconSource;
}

export function StatsCard({
  title,
  value,
  prefix = "",
  suffix = "",
  comparison = 0,
  loading = false,
  icon,
}: StatsCardProps) {
  const isPositive = comparison >= 0;
  const comparisonColor = isPositive ? "success" : "critical";

  if (loading) {
    return (
      <Card>
        <BlockStack gap="200">
          <SkeletonBodyText lines={2} />
        </BlockStack>
      </Card>
    );
  }

  return (
    <Card>
      <BlockStack gap="200">
        <InlineStack align="space-between">
          <Text as="span" variant="bodySm" tone="subdued">
            {title}
          </Text>
          {icon && <Icon source={icon} tone="subdued" />}
        </InlineStack>

        <Text as="p" variant="headingXl" fontWeight="bold">
          {prefix}
          {typeof value === "number" ? value.toLocaleString() : value}
          {suffix}
        </Text>

        <Text as="span" variant="bodySm" tone={comparisonColor}>
          {isPositive ? "+" : ""}
          {comparison.toFixed(1)}% vs last week
        </Text>
      </BlockStack>
    </Card>
  );
}
