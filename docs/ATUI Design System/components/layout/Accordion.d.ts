import * as React from "react";

/**
 * at-accordion / at-accordion-item — collapsible sections.
 */
export interface AccordionProps {
  items?: { label: string;
  content?: React.ReactNode;
  open?: boolean;
  disabled?: boolean }[];
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

export declare function Accordion(props: AccordionProps): React.ReactElement;
