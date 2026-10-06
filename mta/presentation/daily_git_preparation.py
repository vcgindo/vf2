"""Sealed typed-source binding for production GIT chart and custom reads."""
import re

from mta.presentation.context import PublicationUnavailable
from mta.presentation.daily_transit import PATH as TRANSIT_PATH, TRANSPORTER_PATH
from mta.presentation.legacy_ui import BPR_UI_CONFIG
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.selective import image_metadata, image_query
from mta.serialization import digest


NMS_PATH = 'closing/consumer_context/NMSAllItems'
LOCATION_PATH = 'closing/importer/LocationAttributeData'
DESCRIPTION_PATH = 'closing/importer/SiteDescriptionTbl'
PATHS = (TRANSPORTER_PATH, TRANSIT_PATH, NMS_PATH, LOCATION_PATH, DESCRIPTION_PATH)


def location_configuration(run):
    """Port ExpediteProcessor.GetUIConfigAttribute('LocAttr').

    The retained AdminBPR population currently has no visible LocAttr columns.
    Any later visible row must map exactly from LocAttrN to LocationAttributeData
    cN; missing or malformed bindings are unavailable rather than omitted.
    """
    rows = [row for row in BPR_UI_CONFIG
            if str(row.get('ReportName', '')).casefold() == 'adminbpr'
            and str(row.get('Col_Code', '')).casefold().startswith('locattr')
            and row.get('Visible') in (True, 1)]
    bindings = []
    config = []
    seen = set()
    metadata = image_metadata(run, LOCATION_PATH)
    available = {field[0].casefold() for field in metadata.get('fields', ())}
    for row in rows:
        match = re.fullmatch(r'LocAttr([1-9]|1[0-5])', str(row.get('Col_Code', '')),
                             flags=re.IGNORECASE)
        if not match:
            raise PublicationUnavailable('daily_git_dynamic_location_configuration_invalid')
        column = 'c' + match.group(1)
        if column.casefold() not in available:
            raise PublicationUnavailable('daily_git_dynamic_location_binding_missing:' + column)
        if column.casefold() in seen:
            raise PublicationUnavailable('daily_git_dynamic_location_binding_duplicate:' + column)
        seen.add(column.casefold())
        bindings.append((column, column))
        config.append(dict(header=str(row.get('Header', '')).replace('/', ' '),
                           colCode=column, colPosition=0))
    return bindings, config


def sources(run, *, chart):
    """Return trusted SQL relations after all existing seals have been checked."""
    relations = dict(admitted_sources(run))
    paths = ((TRANSPORTER_PATH, TRANSIT_PATH, LOCATION_PATH, DESCRIPTION_PATH)
             if chart else (TRANSPORTER_PATH, TRANSIT_PATH, NMS_PATH, DESCRIPTION_PATH))
    for path in paths:
        image_metadata(run, path)
        relations[path] = image_query(run, path)
    bindings, config = location_configuration(run) if chart else ([], [])
    return relations, bindings, config


def validate_ready(run):
    """Coordinator hook replacing the obsolete nonempty-transit rejection."""
    chart_relations, bindings, config = sources(run, chart=True)
    custom_relations, _, _ = sources(run, chart=False)
    return dict(recipe_digest=recipe_digest(),
                relations=tuple(sorted(set(chart_relations) | set(custom_relations))),
                dynamic_bindings=tuple(bindings), ui_config=tuple(
                    (row['header'], row['colCode'], row['colPosition']) for row in config))


def recipe_digest():
    return digest(dict(version=1, paths=PATHS,
                       locattr=[(row.get('ReportName'), row.get('Col_Code'),
                                 row.get('Header'), row.get('Visible'))
                                for row in BPR_UI_CONFIG
                                if str(row.get('ReportName', '')).casefold() == 'adminbpr'
                                and str(row.get('Col_Code', '')).casefold().startswith('locattr')]))
