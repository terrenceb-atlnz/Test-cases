import * as React from "react";

/**
 * at-chart-trend — metric tile: display value, delta, sparkline.
 */
export interface ChartTrendProps {
  label?: string;
  value: React.ReactNode;
  unit?: string;
  delta?: number;
  good?: "up"|"down";
  data?: number[];
}

export declare function ChartTrend(props: ChartTrendProps): React.ReactElement;
