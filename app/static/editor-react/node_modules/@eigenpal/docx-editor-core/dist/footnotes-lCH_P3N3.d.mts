import { FlowBlock, Measure, TableBlock, FootnoteContent } from './layout-engine/types.mjs';

/**
 * Header / footer rendering for renderPage.
 *
 * Owns `renderHeaderFooterContent` — the mini-flow that lays paragraphs and
 * tables inside a header/footer container (separate from the body flow) —
 * plus the floating-image and floating-table positioning helpers used by
 * that flow. Coordinates returned by `resolveHeaderFooterFloatingTablePosition`
 * are relative to the HF container's flow origin (`layout.flowTop`/`flowLeft`)
 * so callers can drop them into `style.top`/`style.left`.
 */

/**
 * Header/footer content for rendering
 */
interface HeaderFooterContent {
    /** Flow blocks for the header/footer content. */
    blocks: FlowBlock[];
    /** Measurements for the blocks. */
    measures: Measure[];
    /** Total height of the content. */
    height: number;
    /** Top-most visual extent relative to the nominal flow origin. */
    visualTop?: number;
    /** Bottom-most visual extent relative to the nominal flow origin. */
    visualBottom?: number;
}
interface HeaderFooterLayoutInfo {
    flowTop: number;
    flowLeft: number;
    contentWidth: number;
    pageWidth: number;
    pageHeight: number;
    margins: {
        top: number;
        right: number;
        bottom: number;
        left: number;
    };
}
/**
 * Resolve the (left, top) position for a floating table inside a header/
 * footer container, per ECMA-376 §17.4.57. The table's `floating.tblpX/tblpY`
 * are already in pixels (parser converted from twips); `horzAnchor`/
 * `vertAnchor` decide whether the offset is relative to the page, the
 * margins, or the surrounding text/column. Coordinates returned are
 * relative to the HF container's flow origin (`layout.flowTop` /
 * `layout.flowLeft`) so the caller can drop them straight into
 * `style.top` / `style.left`.
 */
declare function resolveHeaderFooterFloatingTablePosition(floating: NonNullable<TableBlock['floating']>, layout: HeaderFooterLayoutInfo): {
    left: number;
    top: number;
};

/**
 * Footnote area rendering.
 *
 * Footnotes get a separator line plus per-item rendering at the bottom of
 * each page. Two paths: measured content (full body pipeline through
 * paragraph/table/image/textBox fragments) for WYSIWYG fidelity, or a plain
 * text fallback when no measurement is available.
 */

/**
 * A single footnote item ready for rendering at page bottom.
 */
interface FootnoteRenderItem {
    /** Display number (e.g. "1", "2") */
    displayNumber: string;
    /** Plain text content */
    text: string;
    /** Measured body-pipeline content used for WYSIWYG painting. */
    content?: FootnoteContent;
}

export { type FootnoteRenderItem as F, type HeaderFooterContent as H, type HeaderFooterLayoutInfo as a, resolveHeaderFooterFloatingTablePosition as r };
