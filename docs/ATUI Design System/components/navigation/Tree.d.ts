import * as React from "react";

/**
 * at-tree / at-tree-item — hierarchical navigation.
 */
export interface TreeProps {
  data: { id: string;
  label: string;
  icon?: string;
  open?: boolean;
  children?: any[] }[];
  selected?: string;
  onSelect?: (id: string) => void;
  style?: React.CSSProperties;
}

export declare function Tree(props: TreeProps): React.ReactElement;
