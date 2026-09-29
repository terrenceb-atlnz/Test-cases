import * as React from "react";

/**
 * at-prompt-thread — scrolling message list.
 */
export interface PromptThreadProps {
  messages: { role: "user"|"assistant";
  content?: React.ReactNode;
  loading?: boolean }[];
  style?: React.CSSProperties;
}

export declare function PromptThread(props: PromptThreadProps): React.ReactElement;
