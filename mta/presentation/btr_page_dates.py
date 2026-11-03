"""Assemble only the dated display cells on an already selected BTR page."""
from datetime import date

from mta.domain.sql_identity_keys import group_key
from mta.presentation import btr_display
from mta.presentation.btr_calendar_sources import _page_cells
from mta.runtime import relational_state as typed


def page_observations(run, directory, pairs):
    observations = {}
    for cell in _page_cells(run, directory, pairs):
        key = group_key(cell.sku, cell.location)
        observations.setdefault(key, {})[cell.business_date] = cell
    return observations


def roster_query(run, item, *, current_colour=False):
    """Scalar roster for private joins. Only the colour filter needs today's cell."""
    from mta.presentation import btr_calendar_images as calendar
    from mta.presentation.btr_calendar_sources import HISTORY, DAILY, TRENDS
    directory = calendar.published_directory(run, item)
    name = item['image'].rsplit('/',1)[1]
    days = {f'D{i}' for i in range(1,91)}
    columns = ['k.vf_ordinal', *('k.'+typed.quote(col) for col,_ in typed.STORAGE_TABLES[item['table']]
                                if col not in days)]
    source = typed.table_sql(item['table']) + ' k'
    bindings = []
    if current_colour:
        operand = TRENDS[name]
        if operand not in ('DispatchColor','PhysicalInventoryColor'):
            raise ValueError('Unexpected BTR current colour filter')
        if directory['daily']:
            table, path, location, dated = 'BPR/vf_RationedReqReport', DAILY, 'WhCode', ''
        else:
            table, path, location, dated = 'BTR/BPR', HISTORY, 'WHCode', ' AND "ReportDate"=%s'
        bindings.extend([run.pk, path])
        if dated:
            bindings.append(run.business_date)
        source += (' LEFT JOIN (SELECT "SKUCode" COLLATE "C" AS sku,'+typed.quote(location)+' COLLATE "C" AS loc,'
                   +'max('+typed.quote(operand)+' COLLATE "C") AS today FROM '+typed.table_sql(table)
                   +' WHERE vf_run_id=%s AND vf_image=%s'+dated+' GROUP BY 1,2) c '
                   +'ON (c.sku IS NULL)=(k."SKUCode" IS NULL) AND (c.loc IS NULL)=(k."WhCode" IS NULL) '
                   +"AND coalesce(c.sku,'')=coalesce(k.\"SKUCode\",'') COLLATE \"C\" "
                   +"AND coalesce(c.loc,'')=coalesce(k.\"WhCode\",'') COLLATE \"C\"")
        columns.append('c.today AS "D90"')
    return ('SELECT '+','.join(columns)+' FROM '+source+' WHERE k.vf_run_id=%s AND k.vf_image=%s',
            bindings+[run.pk,item['image']])


def date_slots(labels, columns):
    return [(column, date.fromisoformat(labels[column])) for column in columns]


def display_dates(branch, row_index, observations, slots, horizon, *, has_colour_row):
    """Keep the original LEFT JOIN, empty-string and display horizon semantics."""
    if branch == 'tech':
        level, colour = 'physical_pen', 'physical_colour'
    elif branch == 'eco':
        level, colour = 'dispatch_pen', 'dispatch_colour'
    else:
        raise ValueError('Unknown BTR display branch')
    levels, colours = {}, {}
    for slot, day in slots:
        cell = observations.get(day)
        value = getattr(cell, level, None)
        tone = getattr(cell, colour, None) if has_colour_row else None
        levels[slot] = '' if value is None else str(value)
        colours['C' + slot] = '' if tone is None else str(tone)
    row = {**levels, **colours}
    result = btr_display.prepare_display({branch: [row]}, horizon)
    # Prepared snapshot readers emit Availability's descriptor before other
    # nonfinite fields; caller inserts scalar descriptors between those groups.
    tokens = {field: [branch, row_index, field, token]
              for _, _, field, token in result['displayNonFinite']}
    return row, tokens
