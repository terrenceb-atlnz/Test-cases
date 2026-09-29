import * as React from "react";

/**
 * at-layout — page scaffolds (page, master-detail).
 */
export interface LayoutProps {
  template?: "page"|"master-detail";
  header?: React.ReactNode;
  master?: React.ReactNode;
  detail?: React.ReactNode;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Layout(props: LayoutProps): React.ReactElement;
