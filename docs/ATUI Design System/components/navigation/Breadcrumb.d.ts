import * as React from "react";

/**
 * at-breadcrumb — trail of links; last item active.
 */
export interface BreadcrumbProps {
  items: { label: string;
  onClick?: () => void }[];
  style?: React.CSSProperties;
}

export declare function Breadcrumb(props: BreadcrumbProps): React.ReactElement;
