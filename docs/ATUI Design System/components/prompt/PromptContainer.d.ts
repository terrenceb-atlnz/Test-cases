import * as React from "react";

/**
 * at-prompt-container — assistant panel (header, thread, composer).
 * @startingPoint section="Prompt" subtitle="assistant panel (header, thread, composer)." viewport="700x300"
 */
export interface PromptContainerProps {
  prompt_title?: string;
  messages?: any[];
  respond?: (text: string) => string;
  style?: React.CSSProperties;
}

export declare function PromptContainer(props: PromptContainerProps): React.ReactElement;
