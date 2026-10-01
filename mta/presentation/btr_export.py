"""Deployed BTR header/layout/date contract; payload Headers is not authoritative."""
from datetime import date
import json

from mta.presentation.context import PublicationUnavailable
from mta.presentation.legacy_ui import UI_CONFIGS

FIELDS = ('Category', 'Availability', 'Tags', 'SKUCode', 'SKUDescription', 'WhCode',
          'LocationName', 'Norm', 'VirtualNorm', 'pc', 'pn',
          *(f'D{i}' for i in range(1, 91)), 'age', 'bc', 'rc', 'yc', 'gc', 'blc', 'wc')


def selected_headers(state, dates):
    try:
        layout = json.loads(state) if state else None
    except (ValueError, TypeError):
        layout = None
    visible = [(r['Header'] or '', r['Col_Code'], r['Col_Position'])
               for r in UI_CONFIGS['BufferTrendReport'] if r['Visible']]
    dynamic = [((date.fromisoformat(str(row[f'D{i}'])[:10]).strftime('%d-%m-%Y')
                 if row[f'D{i}'] is not None else ''), f'D{i}', i + 12)
               for i in range(1, 91) for row in dates]
    if not isinstance(layout, (dict, list)):
        selected = visible + dynamic
    else:
        columns = layout.get('columns', []) if isinstance(layout, dict) else []
        if isinstance(columns, dict):
            raise PublicationUnavailable('BTR_EXPORT_LAYOUT_OBJECT_NOT_VERIFIED')
        if not isinstance(columns, list):
            columns = []
        # SQL UNPIVOT excludes NULL dates in the saved-layout header join.
        metadata = visible + [item for item in dynamic if item[0] != '']
        selected = []
        for position, column in enumerate(columns, 1):
            if not isinstance(column, dict):
                continue
            code, hide = column.get('colId'), column.get('hide')
            if hide is None or isinstance(hide, (dict, list)):
                hide = False
            if code is None or str(hide).lower() != 'false':
                continue
            matches = [item for item in metadata if item[1].casefold() == str(code).casefold()]
            selected.extend((header, code, position) for header, _, _ in matches)
            if not matches:
                selected.append(('', code, position))
    return [(header, code) for header, code, _ in sorted(selected, key=lambda r: r[2])
            if code and str(code).strip() and code in FIELDS]
