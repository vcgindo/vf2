import { mapBTRRowData } from '../../../../../helpers/utils';

/** Old servers remain usable during rollback; prepared rows need no field scan. */
export const displayRows = (data: any, branch: 'tech' | 'eco', horizon: number): any[] => {
    if (data.displayPrepared !== true) return mapBTRRowData(data[branch], horizon);
    const rows = data[branch];
    // JSON cannot represent JS non-finite numbers. Restore only explicitly listed
    // cells, without walking/copying every field or recalculating Availability.
    for (const [source, index, field, value] of data.displayNonFinite || []) {
        if (source === branch) rows[index][field] = value === 'NaN' ? NaN : value === 'Infinity' ? Infinity : -Infinity;
    }
    return rows;
};
