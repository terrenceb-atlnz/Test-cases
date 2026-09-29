import * as React from "react";

/**
 * at-chart-gauge — semicircle gauge with alert thresholds.
 */
export interface ChartGaugeProps {
  value: number;
  max?: number;
  label?: string;
  unit?: string;
  thresholds?: [number, number];
  size?: number;
}

export declare function ChartGauge(props: ChartGaugeProps): React.ReactElement;
