import * as React from "react";

/**
 * at-input-range — bounded magnitudes (%, thresholds) as a slider.
 */
export interface InputRangeProps {
  label?: string;
  hint_text?: string;
  info_text?: string;
  value?: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  show_value?: boolean;
  onChange?: (v: number) => void;
}

export declare function InputRange(props: InputRangeProps): React.ReactElement;
