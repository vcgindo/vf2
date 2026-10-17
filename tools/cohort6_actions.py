"""Password-authenticated, no-listener Cohort6 preacceptance action entry."""
import argparse
import base64
import json
import os
from pathlib import Path


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.cohort6_settings')


FILE_KEYS = ('artifact', 'finalization', 'pick_config', 'shipment')


def _secret(name):
    if not isinstance(name, str) or not name or name not in os.environ:
        raise ValueError('Explicit populated credential environment reference required')
    value = os.environ[name]
    if not value:
        raise ValueError('Explicit populated credential environment reference required')
    return value


def _encrypted_password(password):
    from Crypto.Cipher import AES
    iv = os.urandom(16)
    cipher = AES.new(_secret('SECRET_KEY_FOR_PASSWORD').encode(), AES.MODE_CTR,
                     nonce=b'', initial_value=int.from_bytes(iv, 'big'))
    return base64.b64encode(iv + cipher.encrypt(password.encode())).decode()


def authenticated_context(*, email_environment, password_environment):
    """Run unchanged password login, then authenticate its cookie JWT."""
    from rest_framework.test import APIRequestFactory
    from api.view.auth import UserLoginView
    from api_gateway.views import API_GATEWAY_VIEW
    from api_gateway.interceptors.mta_interceptor import authenticated_mta_context

    factory = APIRequestFactory()
    login = factory.post('/api/user/login/', data={
        'email': _secret(email_environment),
        'password': _encrypted_password(_secret(password_environment)),
    }, format='json')
    response = UserLoginView.as_view()(login)
    cookie = response.cookies.get('access_token')
    if response.status_code != 200 or cookie is None or not cookie.value:
        raise ValueError('Cohort6 password authentication denied')

    raw = factory.post('/api/mta/DBMApplySelectedNorms', data={}, format='json')
    raw.COOKIES['access_token'] = cookie.value
    view = API_GATEWAY_VIEW()
    request = view.initialize_request(raw)
    view.request = request
    view.args = ()
    view.kwargs = {}
    view.perform_authentication(request)
    view.check_permissions(request)
    context = authenticated_mta_context(request, application_id=2)
    # Do not retain the credential beyond authentication and scope projection.
    raw.COOKIES.clear()
    return context


def _access(context):
    from django.conf import settings
    return {
        'product_permissions': context['product_permissions'],
        'location_permissions': context['location_permissions'],
        'permissions_sha256': settings.VF_MTA_PERMISSIONS_SHA256,
        'hierarchy_sha256': settings.VF_MTA_HIERARCHY_SHA256,
    }


def _files(options):
    result = {}
    for name in FILE_KEYS:
        result[name] = {
            'path': str(getattr(options, name).resolve()),
            'sha256': getattr(options, name + '_sha256'),
        }
    return result


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--email-environment', required=True)
    parser.add_argument('--password-environment', required=True)
    mode = parser.add_subparsers(dest='mode', required=True)
    build = mode.add_parser('build-manifest')
    build.add_argument('--output', type=Path, required=True)
    for name in FILE_KEYS:
        build.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
        build.add_argument('--' + name.replace('_', '-') + '-sha256', required=True)
    mode.add_parser('execute')
    return parser


def main(argv=None):
    options = _parser().parse_args(argv)
    import django
    django.setup()
    from mta.runtime.models import CalculationRun
    from development import preacceptance_actions

    principal = authenticated_context(
        email_environment=options.email_environment,
        password_environment=options.password_environment)
    actor = str(principal['actor'])
    access = _access(principal)
    run = CalculationRun.objects.get(pk=options.run)
    if options.mode == 'build-manifest':
        manifest = preacceptance_actions.build_manifest(
            run, actor=actor, access=access, files=_files(options))
        with options.output.open('x', encoding='utf-8') as stream:
            json.dump(manifest, stream, indent=2)
            stream.write('\n')
        result = {'mode': options.mode, 'run_id': str(run.pk),
                  'actor': actor, 'phase_identity': manifest['phase_identity'],
                  'manifest': str(options.output.resolve())}
    else:
        events = preacceptance_actions.execute(run, actor=actor, access=access)
        result = {'mode': options.mode, 'run_id': str(run.pk), 'actor': actor,
                  'event_ids': [str(event.pk) for event in events]}
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == '__main__':
    main()
