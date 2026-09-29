import * as React from "react";

/**
 * at-relative-time — "5 minutes ago" with absolute time in title.
 */
export interface RelativeTimeProps {
  date: string | number | Date;
  style?: React.CSSProperties;
}

export declare function RelativeTime(props: RelativeTimeProps): React.ReactElement;
