import * as React from "react";

/**
 * at-tabs — horizontal underline tabs or vertical list.
 * @startingPoint section="Navigation" subtitle="horizontal underline tabs or vertical list." viewport="700x300"
 */
export interface TabsProps {
  tabs: { id: string;
  title: string;
  suffix?: React.ReactNode }[];
  active_tab?: string;
  layout?: "horizontal"|"vertical";
  fill?: boolean;
  onChange?: (id: string) => void;
  nav_content?: React.ReactNode;
  children?: React.ReactNode | ((active: string) => React.ReactNode);
  style?: React.CSSProperties;
}

export declare function Tabs(props: TabsProps): React.ReactElement;
