"""Build only an independently pinned committed MTA export; never a raw checkout.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

from release.mta_packaging import prepare, files


def build(root, context, wheelhouse, *, commit, source_sha256, native_sha256, image,
          runner=subprocess.run, owner='cleanup-step6-20261017'):
    if not re.fullmatch(r'[a-z0-9][a-z0-9._:/-]{0,199}',image) or ':' not in image:
        raise ValueError('Explicit local MTA image tag required')
    receipt=prepare(root,context,wheelhouse,commit=commit,source_sha256=source_sha256,native_sha256=native_sha256)
    # The verified Dockerfile has a literal pinned non-application base. Reject
    # any attempt to replace its FROM authority via argument or environment.
    base=json.loads((Path(root)/'release/images.lock.json').read_text())['python_mta']
    if base != 'python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d':
        raise ValueError('Reviewed MTA dependency base differs')
    arguments=['docker','build','--pull=false','--network=none','--memory=4g','--memory-swap=4g',
        '--cpu-period=100000','--cpu-quota=200000','--rm=false',
        '--label','vectorflow.owner='+owner,
        '--build-arg','VF_NATIVE_RELEASE_COMMIT='+commit,
        '--build-arg','VF_NATIVE_RELEASE_SHA256='+native_sha256,
        '--build-arg','VF_SOURCE_MANIFEST_SHA256='+source_sha256,
        '--build-arg','PACKAGING_TOOL_SHA256='+receipt['packaging_tool_sha256'],
        '--tag',image,str(Path(context).resolve())]
    import os
    # Legacy builder honors the explicit per-RUN CPU/memory bounds. No new
    # builder container/service/network, no remote dependency access.
    result=runner(arguments,env={**os.environ,'DOCKER_BUILDKIT':'0'},check=False)
    if result.returncode:
        raise ValueError('MTA build failed; preserve its exact stopped attempts')
    return dict(status='MTA_IMAGE_BUILD_COMPLETED_INSPECTION_STILL_REQUIRED',image=image,
        source_commit=commit,source_sha256=source_sha256,native_sha256=native_sha256,
        context_files=receipt['files'],build_arguments=arguments)


def source_zip(root,destination):
    root,destination=Path(root),Path(destination)
    if destination.exists():
        raise ValueError('Archive destination already exists')
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in files(root):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if name.endswith('.sh') else 0o100644)<<16
            archive.writestr(info,(root/name).read_bytes())
    return dict(bytes=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--context',type=Path,required=True)
    parser.add_argument('--wheelhouse',type=Path,required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--native-sha256',required=True)
    parser.add_argument('--image',required=True)
    args=parser.parse_args()
    value=build(args.source_root,args.context,args.wheelhouse,commit=args.commit,
        source_sha256=args.source_sha256,native_sha256=args.native_sha256,image=args.image)
    print(json.dumps(value,sort_keys=True))
