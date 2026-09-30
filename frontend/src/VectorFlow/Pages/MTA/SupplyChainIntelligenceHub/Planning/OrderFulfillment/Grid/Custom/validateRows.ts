/** P1 approved presentation boundary; never manufacture missing NMS identity. */
export function validateCustomRows(rows: unknown): any[] {
    if (!Array.isArray(rows)) {
        throw new Error('Custom view could not be loaded. Return to the normal view or retry later.');
    }
    if (rows.some(row => !row || !row.sc || !row.wc)) {
        throw new Error('Custom view unavailable: the selected NMS snapshot does not provide SKU/location identity for these rows. Use the normal view; no replacement data has been generated.');
    }
    return rows;
}
