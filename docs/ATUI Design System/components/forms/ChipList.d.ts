import * as React from "react";

/**
 * at-chip-list — removable lg badges.
 */
export interface ChipListProps {
  chips: string[];
  type?: "default"|"info"|"success"|"warning"|"error"|"disabled";
  removable?: boolean;
  onChange?: (chips: string[]) => void;
  style?: React.CSSProperties;
}

export declare function ChipList(props: ChipListProps): React.ReactElement;
