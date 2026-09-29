import * as React from "react";

/**
 * at-select — single-choice dropdown.
 * @startingPoint section="Forms" subtitle="single-choice dropdown." viewport="700x300"
 */
export interface SelectProps {
  label?: string;
  hint_text?: string;
  info_text?: string;
  error_text?: string;
  placeholder?: string;
  required?: boolean;
  invalid?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  options: { value: any;
  label?: string;
  disabled?: boolean }[];
  value?: any;
  clearable?: boolean;
  onChange?: (v: any) => void;
  width?: string | number;
}

export declare function Select(props: SelectProps): React.ReactElement;
