import * as React from "react";

/**
 * at-select-option — row inside Select/MultiSelect listboxes.
 */
export interface SelectOptionProps {
  value: any;
  label?: string;
  is_active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  before?: React.ReactNode;
  after?: React.ReactNode;
}

export declare function SelectOption(props: SelectOptionProps): React.ReactElement;
