import * as React from "react";

/**
 * at-chart-breakdown — stacked proportion bar with legend + counts.
 */
export interface ChartBreakdownProps {
  data: { label: string;
  value: number }[];
  palette?: string;
  total_label?: string;
}

export declare function ChartBreakdown(props: ChartBreakdownProps): React.ReactElement;
