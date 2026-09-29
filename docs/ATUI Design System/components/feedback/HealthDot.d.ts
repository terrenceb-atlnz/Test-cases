import * as React from "react";

/**
 * at-health-dot — shape-coded health glyph: circle good, triangle warn, diamond bad.
 */
export interface HealthDotProps {
  status?: "good"|"warn"|"bad";
  size?: "sm"|"md"|"lg";
  style?: React.CSSProperties;
}

export declare function HealthDot(props: HealthDotProps): React.ReactElement;
