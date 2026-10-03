"""MTA-image-only deployment with the retained fixture/catalogue unchanged."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import stage2_fixture_window as window
from tools import stage2_identity_catalogue as catalogue

EVIDENCE = Path('D:/freshvcf-build/evidence/3005-report-contention-20261004-001')


def saved(name):
    return json.loads((EVIDENCE / name).read_text())


def write(name, value):
    with (EVIDENCE / name).open('x') as output:
        json.dump(value, output, indent=2)


def prepare(image):
    catalogue.check_current()
    before = saved('before.json')
    if window.protected() != before['protected'] or window.runtime(window.inspect(window.MTA)) != before['mta']:
        raise ValueError('Baseline runtime changed')
    candidate = json.loads(subprocess.check_output(['docker', 'image', 'inspect', image]))[0]['Id']
    write('compose.candidate.json', dict(services=dict(mta=dict(image=candidate))))
    write('compose.rollback.json', dict(services=dict(mta=dict(image=before['mta']['image']))))
    # Existing fixture policy image_sha256 remains source-serving provenance.
    # Deployment image identity is separately pinned here; admission is unchanged.
    write('deployment.json', dict(candidate_image=candidate, rollback_image=before['mta']['image'],
        selection=catalogue.live_selection(), fixture_compose_sha256=window.sha(window.DEST / 'compose.fixture.json')))


def verify_inputs():
    deployment = saved('deployment.json')
    if window.sha(window.DEST / 'compose.fixture.json') != deployment['fixture_compose_sha256']:
        raise ValueError('Retained fixture deployment configuration changed')
    if catalogue.live_selection() != deployment['selection'] or catalogue.gateway_selection() != deployment['selection']:
        raise ValueError('Coordinated catalogue selection changed')


def verify_runtime(image):
    before = saved('before.json')
    expected = dict(before['mta'], image=image)
    result = dict(protected=window.protected(), mta=window.runtime(window.inspect(window.MTA)), ready=window.ready())
    if result['mta'] != expected or result['protected'] != before['protected'] or result['ready'] != before['ready']:
        raise ValueError('Image-only deployment changed runtime, protected state or admission')
    verify_inputs()
    catalogue.gateway_ready()
    return result


def deploy(rollback=False):
    deployment = saved('deployment.json')
    if rollback:
        # Recovery must work when the candidate cannot become ready. Establish
        # ownership and preserve diagnostics without requiring its health check.
        current = window.inspect(window.MTA)
        before = saved('before.json')
        if current['Image'] != deployment['candidate_image'] or window.protected() != before['protected']:
            raise ValueError('Rollback target or protected resources changed')
        if (window.sha(window.DEST / 'compose.fixture.json') != deployment['fixture_compose_sha256']
                or catalogue.gateway_selection() != deployment['selection']):
            raise ValueError('Rollback configuration or gateway selection changed')
        write('rollback-before.json', dict(mta=window.runtime(current), candidate_readiness_required=False))
    else:
        verify_runtime(deployment['rollback_image'])
    filename = 'compose.rollback.json' if rollback else 'compose.candidate.json'
    target = deployment['rollback_image'] if rollback else deployment['candidate_image']
    if saved(filename) != dict(services=dict(mta=dict(image=target))):
        raise ValueError('Image-only deployment overlay changed')
    subprocess.run(window.COMPOSE + ['-f', str(window.DEST / 'compose.fixture.json'),
        '-f', str(EVIDENCE / filename), 'up', '-d', '--no-deps', '--no-build', 'mta'], check=True)
    result = verify_runtime(target)
    write('rollback.json' if rollback else 'after.json', result)
    print('Image-only runtime, fixed fixture/catalogue and protected state verified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'deploy', 'check', 'rollback'))
    parser.add_argument('--image')
    args = parser.parse_args()
    if args.operation == 'prepare':
        if not args.image: parser.error('--image is required for prepare')
        prepare(args.image)
    elif args.operation == 'check':
        verify_runtime(saved('deployment.json')['candidate_image'])
        catalogue.check_current(EVIDENCE / 'after.json')
        print('Current report runtime and coordinated normal-restoration inputs verified')
    else:
        deploy(rollback=args.operation == 'rollback')
