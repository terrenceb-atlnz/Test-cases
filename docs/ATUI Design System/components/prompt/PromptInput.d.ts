import * as React from "react";

/**
 * at-prompt-input — composer with send/stop.
 */
export interface PromptInputProps {
  placeholder?: string;
  onSend?: (text: string) => void;
  busy?: boolean;
  onStop?: () => void;
}

export declare function PromptInput(props: PromptInputProps): React.ReactElement;
