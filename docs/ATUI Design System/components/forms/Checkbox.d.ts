import * as React from "react";

/**
 * at-checkbox / at-checkbox-group / at-radio / at-radio-group — padded selectable rows.
 * @startingPoint section="Forms" subtitle="padded selectable rows." viewport="700x300"
 */
export interface CheckboxProps {
  label?: string;
  hint_text?: string;
  checked?: boolean;
  disabled?: boolean;
  indeterminate?: boolean;
  onChange?: (checked: boolean) => void;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Checkbox(props: CheckboxProps): React.ReactElement;
