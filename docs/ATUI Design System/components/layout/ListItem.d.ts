import * as React from "react";

/**
 * at-list-item — key:value row with hairline.
 */
export interface ListItemProps {
  item_prefix?: string;
  item_title: string;
  subtitle?: string;
  content?: React.ReactNode;
  size?: "xs"|"sm"|"md"|"lg";
  selectable?: boolean;
  icon?: string;
  children?: React.ReactNode;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export declare function ListItem(props: ListItemProps): React.ReactElement;
