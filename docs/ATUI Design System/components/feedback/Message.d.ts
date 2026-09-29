import * as React from "react";

/**
 * at-message — inline alert/banner; preset types render their own icon.
 * @startingPoint section="Feedback" subtitle="inline alert/banner; preset types render their own icon." viewport="700x300"
 */
export interface MessageProps {
  type?: "default"|"info"|"success"|"warning"|"error";
  impact?: "low"|"high";
  message_title?: string;
  content?: string;
  icon?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Message(props: MessageProps): React.ReactElement;
