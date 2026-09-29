import * as React from "react";

/**
 * at-prompt-message — chat message (user bubble / assistant text + feedback).
 */
export interface PromptMessageProps {
  role?: "user"|"assistant";
  content?: React.ReactNode;
  loading?: boolean;
  show_actions?: boolean;
  children?: React.ReactNode;
}

export declare function PromptMessage(props: PromptMessageProps): React.ReactElement;
