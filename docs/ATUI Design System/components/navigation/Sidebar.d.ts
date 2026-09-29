import * as React from "react";

/**
 * at-sidebar + at-sidebar-menuitem + at-sidebar-submenu — app navigation rail.
 * @startingPoint section="Navigation" subtitle="app navigation rail." viewport="700x300"
 */
export interface SidebarProps {
  header?: React.ReactNode;
  footer?: React.ReactNode;
  collapsed?: boolean;
  side?: "left"|"right";
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Sidebar(props: SidebarProps): React.ReactElement;
