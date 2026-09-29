import * as React from "react";

/**
 * at-time-range — preset relative time ranges.
 */
export interface TimeRangeProps {
  label?: string;
  options?: string[];
  value?: string;
  onChange?: (v: string) => void;
}

export declare function TimeRange(props: TimeRangeProps): React.ReactElement;
