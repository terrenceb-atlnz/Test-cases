import * as React from "react";

/**
 * at-stepper — wizard progress.
 */
export interface StepperProps {
  steps: { title: string;
  subtitle?: string }[];
  current?: number;
  layout?: "horizontal"|"vertical";
  onStepClick?: (i: number) => void;
  style?: React.CSSProperties;
}

export declare function Stepper(props: StepperProps): React.ReactElement;
