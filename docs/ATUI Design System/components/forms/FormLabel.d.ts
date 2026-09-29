import * as React from "react";

/**
 * at-form-label — xs/medium field label with required star and info tooltip.
 */
export interface FormLabelProps {
  label?: string;
  required?: boolean;
  info_text?: string;
  htmlFor?: string;
  style?: React.CSSProperties;
}

export declare function FormLabel(props: FormLabelProps): React.ReactElement;
