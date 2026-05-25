import React__default, { CSSProperties } from 'react';

/**
 * Print Utilities
 *
 * Provides print functionality with:
 * - Print button component for toolbar
 * - Print-specific CSS styles
 * - Browser print dialog trigger
 * - Page range utilities
 */

/**
 * Print options
 */
interface PrintOptions {
    /** Whether to include headers */
    includeHeaders?: boolean;
    /** Whether to include footers */
    includeFooters?: boolean;
    /** Whether to include page numbers */
    includePageNumbers?: boolean;
    /** Page range to print (null = all) */
    pageRange?: {
        start: number;
        end: number;
    } | null;
    /** Scale factor for printing (1.0 = 100%) */
    scale?: number;
    /** Whether to show background colors */
    printBackground?: boolean;
    /** Margins mode */
    margins?: 'default' | 'none' | 'minimum';
}
/**
 * PrintButton props
 */
interface PrintButtonProps {
    /** Callback when print is triggered */
    onPrint: () => void;
    /** Whether the button is disabled */
    disabled?: boolean;
    /** Button label */
    label?: string;
    /** Additional CSS class */
    className?: string;
    /** Additional inline styles */
    style?: CSSProperties;
    /** Show icon */
    showIcon?: boolean;
    /** Compact mode */
    compact?: boolean;
}
/**
 * PrintButton - Standalone print button for toolbar
 */
declare function PrintButton({ onPrint, disabled, label: labelProp, className, style, showIcon, compact, }: PrintButtonProps): React__default.ReactElement;
/**
 * PrintStyles - Injects print-specific CSS
 */
declare function PrintStyles(): React__default.ReactElement;
/**
 * Trigger browser print dialog for the current document
 */
declare function triggerPrint(): void;
/**
 * Create print-optimized document view in a new window
 */
declare function openPrintWindow(title: string | undefined, content: string): Window | null;
/**
 * Get default print options
 */
declare function getDefaultPrintOptions(): PrintOptions;
/**
 * Create page range from string (e.g., "1-5", "3", "1,3,5")
 */
declare function parsePageRange(input: string, maxPages: number): {
    start: number;
    end: number;
} | null;
/**
 * Format page range for display
 */
declare function formatPageRange(range: {
    start: number;
    end: number;
} | null, totalPages: number): string;
/**
 * Check if browser supports good print functionality
 */
declare function isPrintSupported(): boolean;

export { type PrintOptions as P, PrintButton as a, type PrintButtonProps as b, PrintStyles as c, formatPageRange as f, getDefaultPrintOptions as g, isPrintSupported as i, openPrintWindow as o, parsePageRange as p, triggerPrint as t };
