import * as React from "react";

/**
 * at-input-date / at-input-time — date or time field.
 */
export interface InputDateProps {
  label?: string;
  hint_text?: string;
  info_text?: string;
  required?: boolean;
  invalid?: boolean;
  error_text?: string;
  disabled?: boolean;
  value?: string;
  type?: "date"|"time"|"datetime-local";
  onChange?: (v: string) => void;
  width?: string | number;
}

export declare function InputDate(props: InputDateProps): React.ReactElement;
