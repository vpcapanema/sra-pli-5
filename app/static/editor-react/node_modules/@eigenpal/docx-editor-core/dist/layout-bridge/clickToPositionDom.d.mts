/**
 * DOM-based Click-to-Position Mapping
 *
 * Uses the browser's actual rendered DOM to find ProseMirror positions.
 * This is more accurate than geometry-based calculation because it uses
 * the browser's own text rendering with document.elementsFromPoint().
 *
 * DOM elements are tagged with data-pm-start and data-pm-end attributes,
 * enabling binary search to find exact character positions.
 * @packageDocumentation
 * @public
 */
/**
 * Find ProseMirror position from a click using DOM-based detection.
 *
 * @param container - The pages container element
 * @param clientX - Client X coordinate from mouse event
 * @param clientY - Client Y coordinate from mouse event
 * @param zoom - Current zoom level (default 1)
 * @returns ProseMirror position, or null if not found
 */
declare function clickToPositionDom(container: HTMLElement, clientX: number, clientY: number, zoom?: number): number | null;
/**
 * Get selection rectangles for a PM range using DOM-based detection.
 *
 * @param container - The pages container element
 * @param from - Start PM position
 * @param to - End PM position
 * @param overlayRect - Bounding rect of the selection overlay
 * @returns Array of selection rectangles in overlay coordinates
 */
interface DomSelectionRect {
    x: number;
    y: number;
    width: number;
    height: number;
    pageIndex: number;
}
declare function getSelectionRectsFromDom(container: HTMLElement, from: number, to: number, overlayRect: DOMRect): DomSelectionRect[];
/**
 * Get caret position from DOM for a PM position.
 *
 * @param container - The pages container element
 * @param pmPos - ProseMirror position
 * @param overlayRect - Bounding rect of the selection overlay
 * @returns Caret position in overlay coordinates, or null
 */
interface DomCaretPosition {
    x: number;
    y: number;
    height: number;
    pageIndex: number;
}
declare function getCaretPositionFromDom(container: HTMLElement, pmPos: number, overlayRect: DOMRect): DomCaretPosition | null;

export { type DomCaretPosition, type DomSelectionRect, clickToPositionDom, getCaretPositionFromDom, getSelectionRectsFromDom };
