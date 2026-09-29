import * as React from "react";

/**
 * at-src-dest — source → destination pair.
 */
export interface SrcDestProps {
  src: string;
  dest: string;
  src_label?: string;
  dest_label?: string;
  style?: React.CSSProperties;
}

export declare function SrcDest(props: SrcDestProps): React.ReactElement;
