import * as React from "react";

/**
 * at-toggle-switch — on/off switch; applies immediately.
 */
export interface ToggleSwitchProps {
  label?: string;
  hint_text?: string;
  label_position?: "before"|"after";
  show_label?: boolean;
  disabled?: boolean;
  value?: boolean;
  onChange?: (v: boolean) => void;
  style?: React.CSSProperties;
}

export declare function ToggleSwitch(props: ToggleSwitchProps): React.ReactElement;
