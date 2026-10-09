"""Pure reconstruction of explicit supported daily command bindings."""
from copy import deepcopy
import hashlib
import json


PICK_POLICY = 'canonical-tied-order-v1'


def verify_sha256(content, expected, label):
    if (not isinstance(content, bytes) or not isinstance(expected, str)
            or hashlib.sha256(content).hexdigest() != expected):
        raise ValueError(label + ' digest differs')
    return content


def apply_finalization(profile, opening, config_bytes, *, artifact_sha256,
                       config_sha256, business_date):
    """Reconstruct the existing finalization profile and opening binding."""
    verify_sha256(config_bytes, config_sha256, 'Finalization supplement')
    try:
        supplement = json.loads(config_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError('Finalization supplement is unavailable or invalid') from error
    if (not isinstance(supplement, dict)
            or set(supplement) != {
                'schema', 'artifact_sha256', 'configuration', 'opening_complete'}
            or supplement['schema'] != 'generic-finalization-input-v1'
            or supplement['artifact_sha256'] != artifact_sha256):
        raise ValueError('Finalization supplement binding differs')
    result_profile = deepcopy(profile)
    result_opening = deepcopy(opening)
    from mta.application.daily_finalization import configuration, begin
    result_profile['complete_daily'] = deepcopy(supplement['configuration'])
    result_profile['complete_daily_config_sha256'] = config_sha256
    result_profile['complete_daily_artifact_sha256'] = artifact_sha256
    configuration(result_profile)
    if 'complete' in result_opening:
        raise ValueError('Finalization supplement cannot replace existing complete state')
    result_opening['complete'] = deepcopy(supplement['opening_complete'])
    begin(result_opening, business_date)
    return result_profile, result_opening


def apply_pick(profile, config_bytes, policy):
    """Return a deep-copied profile with the exact complete-Pick mapping."""
    if policy != PICK_POLICY:
        raise ValueError('Unsupported complete Pick policy')
    if not isinstance(config_bytes, bytes):
        raise ValueError('Complete Pick configuration is unavailable or invalid')
    try:
        pick_config = json.loads(config_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError('Complete Pick configuration is unavailable or invalid') from error
    if (not isinstance(pick_config, dict)
            or set(pick_config) != {'vehicles', 'location_vehicles'}
            or not isinstance(pick_config['vehicles'], list)
            or not pick_config['vehicles']
            or not isinstance(pick_config['location_vehicles'], list)
            or not pick_config['location_vehicles']):
        raise ValueError(
            'Complete Pick configuration requires exact vehicle and location mappings')
    vehicle_fields = {'vehicle_id', 'name', 'weight_capacity', 'volume_capacity'}
    mapping_fields = {'location_code', 'vehicle_id'}
    if (any(not isinstance(row, dict) or set(row) != vehicle_fields
            for row in pick_config['vehicles'])
            or any(not isinstance(row, dict) or set(row) != mapping_fields
                   for row in pick_config['location_vehicles'])):
        raise ValueError('Complete Pick configuration fields differ')
    vehicle_ids = [row['vehicle_id'] for row in pick_config['vehicles']]
    if (any(isinstance(value, bool) or not isinstance(value, (str, int))
            or value == '' for value in vehicle_ids)
            or any(not isinstance(row['name'], str) or not row['name']
                   or row['weight_capacity'] is None
                   or row['volume_capacity'] is None
                   for row in pick_config['vehicles'])):
        raise ValueError('Complete Pick vehicle identities or mappings differ')
    vehicle_id_set = set(vehicle_ids)
    if (len(vehicle_id_set) != len(vehicle_ids)
            or any(not isinstance(row['location_code'], str)
                   or not row['location_code']
                   or row['vehicle_id'] not in vehicle_id_set
                   for row in pick_config['location_vehicles'])):
        raise ValueError('Complete Pick vehicle identities or mappings differ')

    result = deepcopy(profile)
    logistics = result.get('calculation', {}).get('logistics')
    if not isinstance(logistics, dict) or not isinstance(logistics.get('items'), list):
        raise ValueError('Complete Pick requires existing artifact logistics items')
    required_locations = {row['from_location'] for row in logistics['items']}
    mapped_locations = {row['location_code']
                        for row in pick_config['location_vehicles']}
    if not required_locations <= mapped_locations:
        raise ValueError('Complete Pick parent-location mapping is incomplete')
    logistics.pop('vehicle', None)
    logistics['vehicles'] = deepcopy(pick_config['vehicles'])
    logistics['location_vehicles'] = deepcopy(pick_config['location_vehicles'])
    result['complete_pick'] = {'policy': policy}
    return result


def apply_operational_sources(profile, policy, input_policy, force_policy):
    """Bind the complete existing three-policy operational capture bundle."""
    from mta.application.operational_capture import CAPTURE_POLICY
    from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY
    from mta.application.timeline_controls import FORCE_CAPTURE_POLICY
    if (policy != CAPTURE_POLICY or input_policy != INPUT_CAPTURE_POLICY
            or force_policy != FORCE_CAPTURE_POLICY):
        raise ValueError('Unsupported explicit operational source capture policy')
    values = {
        'operational_sources': policy,
        'operational_input_sources': input_policy,
        'operational_force_sources': force_policy,
    }
    if any(key in profile and profile[key] != value
           for key, value in values.items()):
        raise ValueError('Artifact operational source policy differs')
    result = deepcopy(profile)
    result.update(values)
    return result


def shipment_day(path, expected_sha256, *, artifact_sha256, business_date):
    """Exact registered supplement; never replace declared artifact shipments."""
    from pathlib import Path
    from mta.presentation.daily_shipment_input import load_day
    registrations = json.loads((Path(__file__).resolve().parents[2] / 'baseline/manifest.json').read_text())['retained_resources']
    if expected_sha256 not in {row['sha256'] for row in registrations}:
        raise ValueError('Shipment supplement must be registered')
    return load_day(path, expected_sha256=expected_sha256,
                    base_artifact_sha256=artifact_sha256, business_date=business_date)
