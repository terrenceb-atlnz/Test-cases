import * as React from "react";

/**
 * at-badge — small status/label pill; low impact (tinted) or high impact (solid).
 * @startingPoint section="Feedback" subtitle="small status/label pill; low impact (tinted) or high impact (solid)." viewport="700x300"
 */
export interface BadgeProps {
  label?: string;
  type?: "default"|"info"|"success"|"warning"|"error"|"disabled";
  size?: "sm"|"lg";
  impact?: "low"|"high";
  rounded?: boolean;
  icon?: string;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Badge(props: BadgeProps): React.ReactElement;
