import * as React from "react";

/**
 * at-dashboard — 12-column widget grid; children set span.
 */
export interface DashboardProps {
  columns?: number;
  gap?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Dashboard(props: DashboardProps): React.ReactElement;
