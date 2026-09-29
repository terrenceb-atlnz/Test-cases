import * as React from "react";

/**
 * at-input-numeric — identifiers / unbounded numbers with steppers. Unit goes in the label.
 */
export interface InputNumericProps {
  label?: string;
  hint_text?: string;
  info_text?: string;
  error_text?: string;
  required?: boolean;
  invalid?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  value?: number;
  min?: number;
  max?: number;
  step?: number;
  onChange?: (v: number) => void;
  width?: string | number;
}

export declare function InputNumeric(props: InputNumericProps): React.ReactElement;
