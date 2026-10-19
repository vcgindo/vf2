"""Resolve application data scopes at the authenticated gateway boundary.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import requests

from common.mta_catalogue import CatalogueUnavailable

ADMIN_DATA_ACCESS_POLICY = 'authenticated-admin-current-catalogue-v1'


def _ids(rows):
    if not isinstance(rows, list):
        raise ValueError('Permission rows must be a list')
    result = []
    for row in rows:
        value = row.get('id') if isinstance(row, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).isdigit():
            raise ValueError('Invalid application permission ID')
        result.append(int(value))
    if len(result) != len(set(result)):
        raise ValueError('Duplicate application permission ID')
    return result


def _administrator_scopes(application_id, services):
    # Import lazily: service configuration imports the gateway interceptors.
    from common.mta_catalogue import enabled, payload, remote_payload
    from common.startup_probe import permission_request
    name = {2: 'mta', 3: 'mto'}.get(application_id)
    service = services.get(name, {})
    if not service or service.get('active', True) is not True or service.get('application_id') != application_id:
        raise CatalogueUnavailable('admin_scope_application_unavailable')
    try:
        if name == 'mta':
            value = payload() if enabled() else remote_payload(permission_request(
                'permission_mta', method='GET',
                url=service['base_url'].rstrip('/') + '/api/mta/GetAllPermmision', timeout=(5, 20)))
            return _ids(value['product']), _ids(value['location'])
        response = permission_request('permission_mto', method='GET',
            url=service['base_url'].rstrip('/') + '/GetMTOPermissionDetails/', timeout=(5, 20))
        if response.status_code != 200:
            raise ValueError('MTO permission service unavailable')
        value = response.json()
        data = value['data']
        # A fresh MTO installation has no permission types/data yet. Its native
        # successful response is {}, distinct from an unavailable catalogue.
        if data == {}:
            return [], []
        if not isinstance(data, dict) or not {'Orders', 'Location'} <= data.keys():
            raise ValueError('MTO permission populations missing')
        def population(key):
            rows = data[key]
            if rows == []:
                return []
            if not isinstance(rows, list) or len(rows) != 1:
                raise ValueError('MTO permission population shape differs')
            return _ids(rows[0])
        return population('Orders'), population('Location')
    except CatalogueUnavailable:
        raise
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        raise CatalogueUnavailable('admin_scope_catalogue_unavailable') from error


def effective_data_scopes(user_id, application_id, *, administrator=False, services=None):
    """Only the caller's authenticated server-side admin flag may expand scopes.

    No effective grant is cached or persisted. Ordinary users keep their exact
    stored grants, including immediate revocation. An empty scope is never '*'.
    """
    if administrator is True:
        if services is None:
            from api_gateway.service_config.config import service_map
            services = service_map
        return _administrator_scopes(application_id, services)
    from api.models import User_Application_Product_Permission, User_Application_Location_Permission
    return (
        list(User_Application_Product_Permission.objects.filter(
            application_id=application_id, user_id=user_id).values_list('productfilter_id', flat=True)),
        list(User_Application_Location_Permission.objects.filter(
            application_id=application_id, user_id=user_id).values_list('locationfilter_id', flat=True)),
    )
