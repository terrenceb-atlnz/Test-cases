import * as React from "react";

/**
 * at-button-group (segmented control) and at-button-switch (Off/On).
 */
export interface ButtonGroupProps {
  label?: string;
  hint_text?: string;
  info_text?: string;
  options: { value: string;
  label?: string;
  icon?: string;
  disabled?: boolean }[];
  value?: string;
  disabled?: boolean;
  onChange?: (v: string) => void;
}

export declare function ButtonGroup(props: ButtonGroupProps): React.ReactElement;
