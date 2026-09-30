/** P4b approved failure presentation; no substitute query or result. */
export function excessFailureMessage(error: any): string {
    let body = error?.response?.data ?? error?.response;
    if (body?.error === 'Failed to forward request' && typeof body.message === 'string') {
        try { body = JSON.parse(body.message); } catch { body = null; }
    }
    if (body?.error === 'legacy_source_flaw' && body?.packet === 'P4b X1') {
        return 'Excess inventory results are unavailable for the selected filters because the legacy query fails. Reset the filters to return to the working view. No replacement results have been generated.';
    }
    return 'Excess inventory could not be loaded. Retry or change the filters. The previous grid is not a result for this request.';
}
