import * as React from "react";

/**
 * at-multi-select — dropdown of checkboxes; selection as chips.
 */
export interface MultiSelectProps {
  label?: string;
  hint_text?: string;
  info_text?: string;
  required?: boolean;
  placeholder?: string;
  options: { value: any;
  label?: string }[];
  value?: any[];
  disabled?: boolean;
  onChange?: (v: any[]) => void;
  width?: string | number;
}

export declare function MultiSelect(props: MultiSelectProps): React.ReactElement;
