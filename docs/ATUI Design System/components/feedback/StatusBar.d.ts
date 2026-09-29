import * as React from "react";

/**
 * at-status-bar — segmented proportion bar.
 */
export interface StatusBarProps {
  segments: { value: number;
  color: string;
  label?: string }[];
  size?: "sm"|"lg";
  style?: React.CSSProperties;
}

export declare function StatusBar(props: StatusBarProps): React.ReactElement;
