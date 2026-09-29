import * as React from "react";

/**
 * at-resizable-group/panel/handle — draggable split.
 */
export interface ResizableProps {
  direction?: "horizontal"|"vertical";
  initial?: number;
  min?: number;
  first: React.ReactNode;
  second: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Resizable(props: ResizableProps): React.ReactElement;
