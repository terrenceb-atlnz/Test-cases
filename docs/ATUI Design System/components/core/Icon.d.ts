import * as React from "react";

/**
 * at-icon — IBM Carbon icon (16px default) that takes the surrounding text colour.
 */
export interface IconProps {
  name?: string;
  carbon?: string;
  size?: number | "xs"|"sm"|"md"|"lg";
  color?: string;
  title?: string;
  style?: React.CSSProperties;
}

export declare function Icon(props: IconProps): React.ReactElement;
