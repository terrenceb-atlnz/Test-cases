import * as React from "react";

/**
 * at-chart-sparkline — tiny inline trend.
 */
export interface ChartSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  area?: boolean;
}

export declare function ChartSparkline(props: ChartSparklineProps): React.ReactElement;
