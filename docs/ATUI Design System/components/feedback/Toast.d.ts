import * as React from "react";

/**
 * at-toaster — transient toast (and the fixed Toaster stack).
 * @startingPoint section="Feedback" subtitle="transient toast (and the fixed Toaster stack)." viewport="700x300"
 */
export interface ToastProps {
  type?: "info"|"success"|"warning"|"error";
  toast_title?: string;
  message?: string;
  action?: React.ReactNode;
  onClose?: () => void;
  progress?: number;
  style?: React.CSSProperties;
}

export declare function Toast(props: ToastProps): React.ReactElement;
