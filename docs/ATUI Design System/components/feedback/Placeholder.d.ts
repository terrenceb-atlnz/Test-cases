import * as React from "react";

/**
 * at-placeholder — empty / zero state.
 */
export interface PlaceholderProps {
  placeholder_title?: string;
  content?: string;
  icon?: string;
  size?: "sm"|"md";
  actions?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Placeholder(props: PlaceholderProps): React.ReactElement;
