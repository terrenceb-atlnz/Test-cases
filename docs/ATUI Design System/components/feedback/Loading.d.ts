import * as React from "react";

/**
 * at-loading — spinner, dots, typing or wave indicator.
 */
export interface LoadingProps {
  variant?: "spinner"|"dots"|"typing"|"wave";
  type?: "default"|"error"|"secondary";
  size?: "sm"|"md"|"lg";
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Loading(props: LoadingProps): React.ReactElement;
