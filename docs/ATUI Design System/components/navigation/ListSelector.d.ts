import * as React from "react";

/**
 * at-list-selector — selectable list with title/subtitle rows.
 */
export interface ListSelectorProps {
  options: { id: string;
  title: string;
  subtitle?: string;
  icon?: string }[];
  selected?: string;
  onSelect?: (id: string) => void;
  style?: React.CSSProperties;
}

export declare function ListSelector(props: ListSelectorProps): React.ReactElement;
