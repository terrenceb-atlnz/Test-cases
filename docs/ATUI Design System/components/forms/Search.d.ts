import * as React from "react";

/**
 * at-search — search box with leading glyph and clear.
 */
export interface SearchProps {
  label?: string;
  hint_text?: string;
  placeholder?: string;
  value?: string;
  onChange?: (v: string) => void;
  width?: string | number;
  style?: React.CSSProperties;
}

export declare function Search(props: SearchProps): React.ReactElement;
