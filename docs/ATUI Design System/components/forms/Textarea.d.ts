import * as React from "react";

/**
 * at-textarea — multi-line input with optional counter.
 */
export interface TextareaProps {
  label?: string;
  hint_text?: string;
  info_text?: string;
  error_text?: string;
  placeholder?: string;
  required?: boolean;
  invalid?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  value?: string;
  rows?: number;
  max_length?: number;
  onChange?: (v: string) => void;
}

export declare function Textarea(props: TextareaProps): React.ReactElement;
