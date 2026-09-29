import * as React from "react";

/**
 * at-input — text input with label, hint, info, validation and clear.
 * @startingPoint section="Forms" subtitle="text input with label, hint, info, validation and clear." viewport="700x300"
 */
export interface InputProps {
  label?: string;
  type?: "text"|"url"|"email"|"password"|"number";
  hint_text?: string;
  info_text?: string;
  error_text?: string;
  placeholder?: string;
  required?: boolean;
  invalid?: boolean;
  readonly?: boolean;
  disabled?: boolean;
  clearable?: boolean;
  value?: string;
  onChange?: (v: string) => void;
  actions?: React.ReactNode;
  width?: string | number;
  style?: React.CSSProperties;
}

export declare function Input(props: InputProps): React.ReactElement;
