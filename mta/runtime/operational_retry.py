"""Reuse exact retained ZIP bytes on an explicitly linked operational retry."""
import os
from pathlib import Path, PurePosixPath
import shutil
from mta.application import operational_io as files
from mta.runtime.operational_lease import require_attempt_lease
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_repair import verify_file_direct


def retry_archive_writer(owner, *, executable, tool_sha256):
    def archive(*, root, staging, members, destination):
        require_attempt_lease(owner)
        if Path(root).resolve() != Path(owner.root).resolve():
            raise ValueError('Retry archive root differs from its owned attempt')
        files.tool_identity(executable, tool_sha256)
        target = files.owned_path(root, destination)
        stage = files.owned_path(root, staging)
        if target.exists() or not stage.is_dir() or not members or len(members) != len(set(members)):
            raise ValueError('New archive destination and explicit unique staged members required')
        wanted = {}
        for name in members:
            if (not isinstance(name, str) or name.startswith(('-', '@'))
                    or any(char in name for char in '*?') or len(PurePosixPath(name).parts) != 1):
                raise ValueError('Canonical batch archive uses flat members')
            receipt = files.inspect_file(stage, name)
            wanted[name] = (receipt['sha256'], receipt['size_bytes'])
        current = owner.operations.get(status='RUNNING')
        specification = {key: getattr(current, key) for key in ('ordinal','group','name','stage','source_digest')}
        previous_id = owner.retry_of_id
        seen = {owner.pk}
        while previous_id is not None:
            if previous_id in seen:
                raise ValueError('Cyclic operational retry lineage')
            seen.add(previous_id)
            previous = OperationalAttempt.objects.get(pk=previous_id)
            if previous.status != 'FAILED' or any(getattr(previous, key) != getattr(owner, key) for key in
                    ('run_id','configuration_id','predecessor_id','run_output_digest','action_digest',
                     'source_digest','business_date','clock')):
                raise ValueError('Retained retry archive owner differs')
            effects = previous.operations.filter(**specification)
            for effect in effects:
                for original in effect.files.filter(relative_path=destination):
                    if not files.owned_path(previous.root, destination).exists():
                        continue
                    verify_file_direct(original)
                    retained = list(original.members.order_by('ordinal').values(
                        'ordinal','name','sha256','size_bytes'))
                    if {row['name']:(row['sha256'],row['size_bytes']) for row in retained} != wanted:
                        raise ValueError('Retained archive differs from retry producer members')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with files.owned_path(previous.root, destination).open('rb') as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output, 1024*1024)
                        output.flush()
                        os.fsync(output.fileno())
                    receipt = dict(relative_path=destination, sha256=original.sha256, size_bytes=original.size_bytes)
                    files.verify_file(root, receipt)
                    if files.zip_members(root, destination) != retained:
                        raise ValueError('Retained archive copy changed')
                    require_attempt_lease(owner)
                    return dict(file=receipt, members=retained, tool_sha256=tool_sha256,
                                reused_from_file=original.pk)
            previous_id = previous.retry_of_id
        result = files.archive_files(root, staging=staging, members=members, destination=destination,
                                     executable=executable, tool_sha256=tool_sha256)
        require_attempt_lease(owner)
        return result
    return archive
