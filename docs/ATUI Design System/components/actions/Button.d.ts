import * as React from "react";

/**
 * at-button — the ATUI button primitive. One primary per view.
 * @startingPoint section="Actions" subtitle="the ATUI button primitive. One primary per view." viewport="700x300"
 */
export interface ButtonProps {
  label?: string;
  type?: "primary"|"primaryOutline"|"primaryText"|"secondary"|"secondaryOutline"|"secondaryText"|"destructive"|"destructiveOutline"|"destructiveText";
  size?: "sm"|"md"|"lg";
  disabled?: boolean;
  in_progress?: boolean;
  icon?: string;
  icon_after?: string;
  title?: string;
  onClick?: (e: any) => void;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Button(props: ButtonProps): React.ReactElement;
