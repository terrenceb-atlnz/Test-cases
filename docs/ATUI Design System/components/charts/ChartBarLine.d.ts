import * as React from "react";

/**
 * at-chart-bar-line — bar and/or line series.
 * @startingPoint section="Charts" subtitle="bar and/or line series." viewport="700x300"
 */
export interface ChartBarLineProps {
  labels: string[];
  series: { name: string;
  data: number[];
  type?: "bar"|"line" }[];
  palette?: "categorical"|"sequential"|"alert"|"device-status"|"onboarding-status"|"events";
  height?: number;
  stacked?: boolean;
  show_legend?: boolean;
}

export declare function ChartBarLine(props: ChartBarLineProps): React.ReactElement;
