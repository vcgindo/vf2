/** The existing command DTOs, shared by their single and batch callers. */
const etaValue = (value: unknown): string | null => {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string') throw new Error('ETA must be a date value');
  return value.replace(/-/g, '/');
};

export const mapTransitRemarkRow = (row: any) => ({
  OrderNo: row.OrderNo,
  SKUCode: row.SKUCode,
  WhCode: row.ReceiverLoc,
  ParentWHCode: row.SenderLocation ?? null,
  Remarks: row.remark ?? row.action ?? row.Action ?? null,
  CurrentLocation: row.CurrentLoc ?? null,
  ETA: etaValue(row.ETA),
});

export const mapTransitRemarkBatch = (rows: any[]) => ({data: rows.map(mapTransitRemarkRow)});

export const mapExpediteActionBatch = (rows: any[]) => ({
  data: rows.map(row => ({
    SKUCode: row.sc,
    WHCode: row.wc,
    Remark: row.action ?? null,
    ETA: etaValue(row.eta),
  })),
});

export const mapPlanningRequest = (row: any, request: string) => {
  if (!row || Array.isArray(row) || typeof row.sc !== 'string' || typeof row.wc !== 'string') {
    throw new Error('Select the request row first');
  }
  if (!Object.prototype.hasOwnProperty.call(row, 'parentWhCode') || row.parentWhCode === undefined) {
    throw new Error('Selected row is missing its parent location code');
  }
  return {
    skuCode: row.sc,
    whCode: row.wc,
    parentWhCode: row.parentWhCode,
    request,
    eta: etaValue(row.eta),
  };
};
