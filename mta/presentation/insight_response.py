"""GuidedInsightsProcessor's scalar SQL JSON empty-result contract."""


def scalar_json_rows(rows):
    # Every selected method reads SELECT (SELECT ... FOR JSON PATH), then
    # maps DBNull.ToString()=="" to null. This is not an empty JSON array.
    return rows if rows else None


def chronic_grid_payload(rows):
    """Restore SQL numeric JSON for the two persisted decimal-string fields."""
    result=[]
    for row in rows:
        value={k:v for k,v in row.items() if k not in ('SKUCode','WHCode') and v is not None}
        for field in ('PhysicalInventoryPen','PipelineInventoryPen'):
            if field in value: value[field]=float(value[field])
        result.append(value)
    return scalar_json_rows(result)
