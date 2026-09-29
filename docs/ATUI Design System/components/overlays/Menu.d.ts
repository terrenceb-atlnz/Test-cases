import * as React from "react";

/**
 * at-menu + at-menu-item — dropdown/context menu.
 * @startingPoint section="Overlays" subtitle="dropdown/context menu." viewport="700x300"
 */
export interface MenuProps {
  trigger: React.ReactNode;
  items?: { label?: string;
  icon?: string;
  onClick?: () => void;
  is_active?: boolean;
  disabled?: boolean;
  divider?: boolean }[];
  children?: React.ReactNode;
  position?: "top"|"bottom";
  align?: "start"|"end";
  width?: number;
  open?: boolean;
  onOpenChange?: (o: boolean) => void;
  autoclose?: boolean;
}

export declare function Menu(props: MenuProps): React.ReactElement;
