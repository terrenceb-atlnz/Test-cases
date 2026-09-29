import * as React from "react";

/**
 * at-side-panel — slide-in panel for detail/peek and short forms.
 */
export interface SidePanelProps {
  open: boolean;
  onClose?: () => void;
  panel_title?: string;
  panel_subtitle?: string;
  size?: "xs"|"sm"|"md"|"lg"|"xl";
  origin?: "left"|"right";
  backdrop?: boolean;
  close_backdrop?: boolean;
  has_close_button?: boolean;
  padding?: boolean;
  position?: "fixed"|"absolute";
  actions?: React.ReactNode;
  title?: React.ReactNode;
  footer?: React.ReactNode;
  children?: React.ReactNode;
}

export declare function SidePanel(props: SidePanelProps): React.ReactElement;
