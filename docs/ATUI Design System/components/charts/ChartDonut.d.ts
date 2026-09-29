import * as React from "react";

/**
 * at-chart-donut — ring with centre total + legend.
 * @startingPoint section="Charts" subtitle="ring with centre total + legend." viewport="700x300"
 */
export interface ChartDonutProps {
  data: { label: string;
  value: number }[];
  palette?: string;
  size?: number;
  center_label?: string;
  show_legend?: boolean;
}

export declare function ChartDonut(props: ChartDonutProps): React.ReactElement;
