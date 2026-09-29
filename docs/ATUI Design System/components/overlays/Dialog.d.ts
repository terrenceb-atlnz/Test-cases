import * as React from "react";

/**
 * at-dialog — modal; slot a Card with title + footer actions.
 * @startingPoint section="Overlays" subtitle="modal; slot a Card with title + footer actions." viewport="700x300"
 */
export interface DialogProps {
  open: boolean;
  onClose?: (reason: string) => void;
  close_backdrop?: boolean;
  close_esc?: boolean;
  backdrop?: boolean;
  width?: string | number;
  aria_label?: string;
  children: React.ReactNode;
}

export declare function Dialog(props: DialogProps): React.ReactElement;
