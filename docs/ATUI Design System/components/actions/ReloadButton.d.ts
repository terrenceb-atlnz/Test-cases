import * as React from "react";

/**
 * at-reload-button — outline icon button that spins while data reloads.
 */
export interface ReloadButtonProps {
  label?: string;
  size?: "sm"|"md"|"lg";
  in_progress?: boolean;
  onClick?: () => void;
}

export declare function ReloadButton(props: ReloadButtonProps): React.ReactElement;
