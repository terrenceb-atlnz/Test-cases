import * as React from "react";

/**
 * at-progress-bar — rounded determinate / indeterminate bar.
 */
export interface ProgressBarProps {
  percentage?: number;
  mode?: "determinate"|"indeterminate";
  type?: "info"|"success"|"warning"|"error";
  size?: "sm"|"lg";
  label_before?: React.ReactNode;
  label_after?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function ProgressBar(props: ProgressBarProps): React.ReactElement;
