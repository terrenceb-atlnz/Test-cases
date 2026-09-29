import * as React from "react";

/**
 * at-tooltip — dark overlay bubble on hover/focus.
 */
export interface TooltipProps {
  content: React.ReactNode;
  position?: "top"|"bottom"|"left"|"right";
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Tooltip(props: TooltipProps): React.ReactElement;
