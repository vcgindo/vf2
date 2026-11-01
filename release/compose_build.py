"""Docker build-stage preparation from the committed Git tree, never a runtime installer.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from release.build_release import wheels
from release.export import export
from release.mta_packaging import prepare


def require_clean(repository):
    # Windows checkout conversion may normalize CRLF even in older mixed-EOL
    # blobs. Only CR-at-EOL differences are ignored; spaces and real edits fail.
    # The exported bytes still come exclusively from Git objects, not this tree.
    subprocess.run(['git', '-C', str(repository), '-c', 'core.safecrlf=false',
                    'diff', '--ignore-cr-at-eol', '--exit-code', 'HEAD'], check=True)


def build(repository, output):
    repository, output = Path(repository), Path(output)
    if not (repository / '.git').is_dir():
        raise ValueError('Build from a fresh Git clone, not a copied tree or linked worktree')
    require_clean(repository)
    commit = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD']).decode().strip()
    output.mkdir()
    record = export(repository, commit, output / 'export')
    assert record['source_commit'] == commit
    frontend = output / 'export/frontend'
    parent = json.loads((frontend / 'tsconfig.json').read_text()).get('extends')
    if parent != './tsconfig.paths.json' or not (frontend / parent).is_file():
        raise ValueError('Required frontend configuration missing from export')
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    source_sha = sha(output / 'export/release-source.json')
    native_sha = sha(output / 'export/release-native-source.json')
    wheels(output / 'export', output / 'wheels')
    context = prepare(output / 'export', output / 'mta-context', output / 'wheels',
                      commit=commit, source_sha256=source_sha, native_sha256=native_sha)
    identity = dict(source_commit=commit, source_sha256=source_sha, native_sha256=native_sha,
                    packaging_tool_sha256=context['packaging_tool_sha256'])
    (output / 'identity.json').write_bytes((json.dumps(identity, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(identity, sort_keys=True))


if __name__ == '__main__':
    build(*sys.argv[1:])
