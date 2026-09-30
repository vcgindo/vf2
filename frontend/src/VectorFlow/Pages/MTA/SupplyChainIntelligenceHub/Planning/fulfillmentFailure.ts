/** Explain only the evidenced P1 failure; do not expose backend SQL or tokens. */
export function fulfillmentFailureMessage(error: any): string | null {
    // axios-config rejects a normalized error whose response is already the body.
    // Also accept raw Axios errors for callers that have not used that interceptor.
    let body = error?.response?.data ?? error?.response;
    if (typeof body?.message === 'string') {
        try { body = JSON.parse(body.message); } catch { return null; }
    }
    if (body?.source_id !== 'B1-SOURCE-08' || body?.status !== 'FAILED_INCOMPARABLE') return null;
    return 'This filter is unavailable in the legacy Fulfilment implementation. Remove the availability/category or colour-age/count filter and apply again. No successful result has been produced for this selection.';
}
