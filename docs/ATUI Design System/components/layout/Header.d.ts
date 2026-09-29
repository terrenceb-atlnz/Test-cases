import * as React from "react";

/**
 * at-header — page/section title row with subtitle and actions.
 */
export interface HeaderProps {
  header_title?: string;
  subtitle?: string;
  size?: "h1"|"h2"|"h3"|"h4"|"h5"|"h6";
  border?: boolean;
  padding?: boolean;
  title_prefix?: React.ReactNode;
  title_suffix?: React.ReactNode;
  subtitle_content?: React.ReactNode;
  actions?: React.ReactNode;
  icon?: string;
  style?: React.CSSProperties;
}

export declare function Header(props: HeaderProps): React.ReactElement;
