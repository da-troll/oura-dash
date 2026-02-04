import { TooltipProps } from "recharts";

interface ChartTooltipProps extends TooltipProps<number, string> {
  unit?: string;
  precision?: number;
  valueFormatter?: (value: number) => string;
}

export function ChartTooltip({
  active,
  payload,
  label,
  unit = "",
  precision = 1,
  valueFormatter,
}: ChartTooltipProps) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const value = payload[0].value;
  const name = payload[0].name;

  // Format the value
  const formattedValue = valueFormatter
    ? valueFormatter(value as number)
    : typeof value === "number"
      ? value.toFixed(precision)
      : value;

  return (
    <div className="rounded-lg border bg-background p-3 shadow-lg">
      <div className="grid gap-2">
        <div className="flex items-center justify-between gap-4">
          <span className="text-sm font-medium text-muted-foreground">
            {label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: payload[0].color }}
          />
          <span className="text-sm font-medium">{name}:</span>
          <span className="text-sm font-bold">
            {formattedValue}
            {unit}
          </span>
        </div>
      </div>
    </div>
  );
}
