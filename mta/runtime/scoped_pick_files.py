"""Required Pick files derived from one accepted BPR phase, never live tables.

The receipt covers only Pick files. It neither acknowledges a scope nor makes
RuntimeReports, other downloads, a UI view or the next predecessor ready.
"""
import hashlib
import inspect
import os
from pathlib import Path
from contextlib import contextmanager,ExitStack
import shutil
import stat
import uuid

from django.db import connection, transaction
from mta.serialization import digest


class PickFilesUnavailable(ValueError):
    pass


def verify_guards():
    """Require the exact new custody guard as well as its no-truncate owner."""
    from importlib import import_module
    created=import_module('mta.runtime.migrations.0193_scope_pick_files')
    accepted=import_module('mta.runtime.migrations.0169_accepted_state_ownership')
    expected=dict(guard_scope_pick_files=created.SQL.split('$guard$')[1],
                  deny_accepted_truncate=accepted.TRUNCATE_BODY,
                  ingestion_watch=import_module('mta.runtime.migrations.0196_scope_pick_capture_key').NEW)
    with connection.cursor() as cursor:
        from mta.runtime.ingestion_ownership import scoped_derived_body
        expected['ingestion_watch']=scoped_derived_body(cursor,minimum='0196_scope_pick_capture_key')
        cursor.execute("SELECT T.tgname,T.tgenabled,T.tgtype,N.nspname,P.proname,T.tgnargs,T.tgqual::text,"
            "T.tgdeferrable,T.tginitdeferred FROM pg_trigger T JOIN pg_proc P ON P.oid=T.tgfoid "
            "JOIN pg_namespace N ON N.oid=P.pronamespace "
            "WHERE T.tgrelid=to_regclass('mta.fresh_mta_scopepickfiles') AND NOT T.tgisinternal ORDER BY 1")
        if cursor.fetchall()!=[
                ('ingestion_watch_delete','O',8,'mta','ingestion_watch',1,None,False,False),
                ('ingestion_watch_insert','O',4,'mta','ingestion_watch',1,None,False,False),
                ('ingestion_watch_truncate','O',32,'mta','ingestion_watch',1,None,False,False),
                ('ingestion_watch_update','O',16,'mta','ingestion_watch',1,None,False,False),
                ('scope_pick_files_immutable','O',31,'mta','guard_scope_pick_files',0,None,False,False),
                ('scope_pick_files_no_truncate','O',34,'mta','deny_accepted_truncate',0,None,False,False)]:
            raise PickFilesUnavailable('Scope Pick file guard coverage differs')
        cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname,"
            "P.prorettype='trigger'::regtype,P.proowner=C.relowner,"
            "NOT EXISTS(SELECT 1 FROM aclexplode(COALESCE(P.proacl,acldefault('f',P.proowner))) A "
            "WHERE A.grantee<>P.proowner) FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
            "JOIN pg_language L ON L.oid=P.prolang CROSS JOIN pg_class C "
            "WHERE C.oid=to_regclass('mta.fresh_mta_scopepickfiles') AND N.nspname='mta' "
            "AND P.proname=ANY(%s) ORDER BY P.proname",[list(expected)])
        if cursor.fetchall()!=[(name,body,name=='ingestion_watch',['search_path=pg_catalog, mta'],'plpgsql',True,True,True)
                               for name,body in sorted(expected.items())]:
            raise PickFilesUnavailable('Scope Pick file custody function differs')


# Qualified old receipts included this reader's source in their recipe, even
# though its compatibility checks do not produce file bytes. Keep their original
# identities; recognize them only while the exact file formatter is unchanged.
_LEGACY_FORMATTER = '3bbb1305268b1ec6298f7a34f49679ff6c48717855e0d0ed3720b0c589a37407'
_LEGACY_RECIPES = frozenset((
    '9c8b5606f377c02301f2b8bec03eff49471631a1958287925876af3ab23743c4',
    'f0351138a54a686cdafb24fad5536b1453001cf0163d877d4c7b5e6c662d1150',
))


def _formatter_digest():
    from mta.application import complete_daily_batch_files, complete_daily_pick_files
    return digest(dict(writer=inspect.getsource(complete_daily_batch_files),
        projections=inspect.getsource(complete_daily_pick_files)))


def recipe_digest():
    return digest(dict(schema='fresh-scoped-pick-sqlcmd-format-v1',formatter=_formatter_digest()))


def _compatible_recipe(recipe):
    return recipe == recipe_digest() or (recipe in _LEGACY_RECIPES
        and _formatter_digest() == _LEGACY_FORMATTER)


def _accepted(phase_id, expected_digest):
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.scope_execution import receipt_digest
    from mta.runtime import phase_state
    phase=RunPhaseAcceptance.objects.select_related('snapshot','attempt','run').get(pk=phase_id)
    image=phase.snapshot
    capture=MdmDailyInputCapture.objects.get(run=phase.run)
    if (phase.phase not in ('PRE_BPR','BPR','DBM') or not phase.state_sealed
            or phase.digest!=expected_digest or phase.digest!=receipt_digest(phase)
            or phase.run.kind!='DAILY_CHAIN' or phase.run.status not in ('RUNNING','SUCCEEDED')
            or phase.source_id!=capture.source_id or phase.capture_digest!=capture.revision_digest
            or phase.input_digest!=phase.run.input_digest
            or phase.attempt.input_manifest_digest!=phase.run.input_manifest_digest
            or capture.status not in ('CAPTURED','CONSUMED') or image is None
            or image.acceptance_id!=phase.pk or image.run_id!=phase.run_id or image.phase!=phase.phase
            or image.input_digest!=phase.input_digest or not phase_state.contract.compatible(image)
            or image.state_digest!=digest(image.manifest)
            or phase.metadata.get('snapshot_digest')!=image.state_digest
            or phase.metadata.get('effect_digest')!=digest(phase.metadata.get('effects'))):
        raise PickFilesUnavailable('Pick files require their exact accepted phase')
    if phase.phase!='PRE_BPR':
        parent=image.parent
        expected='PRE_BPR' if phase.phase=='BPR' else 'BPR'
        if parent is None or parent.acceptance_id is None:
            raise PickFilesUnavailable('Pick phase parent is absent')
        prior=_accepted(parent.acceptance_id,phase.metadata.get('effects',{}).get('parent_acceptance_digest'))
        if prior.phase!=expected or prior.run_id!=phase.run_id or prior.source_id!=phase.source_id:
            raise PickFilesUnavailable('Pick phase parent differs')
    return phase


def _binding(phase_id, expected_digest):
    from mta.runtime.input_reader import read_input
    verify_guards()
    phase=_accepted(phase_id,expected_digest)
    if phase.phase=='DBM':
        phase=_accepted(phase.snapshot.parent.acceptance_id,
            phase.metadata['effects']['parent_acceptance_digest'])
    if phase.phase!='BPR':
        raise PickFilesUnavailable('Pick files require accepted BPR ownership')
    raw=read_input(phase.run,components=('profile','pick_output_root'))
    if (raw['profile'].get('complete_pick')!={'policy':'canonical-tied-order-v1'}
            or not isinstance(raw.get('pick_output_root'),str) or not raw['pick_output_root']):
        raise PickFilesUnavailable('Captured complete Pick policy and owned root required')
    root=Path(raw['pick_output_root'])
    if not root.is_absolute() or str(root)!=str(root.resolve(strict=True)) or not root.is_dir():
        raise PickFilesUnavailable('Captured canonical Pick root is unavailable')
    return phase,root


@contextmanager
def _folder(parent, name, *, create=False, exclusive=False):
    if not name or name in ('.','..') or '/' in name or '\\' in name:
        raise PickFilesUnavailable('Pick directory component differs')
    try:
        if create:
            try:os.mkdir(name,mode=0o700,dir_fd=parent);os.fsync(parent)
            except FileExistsError:
                if exclusive:raise
        descriptor=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
    except OSError as error:
        raise PickFilesUnavailable('Pick file directory is absent, linked or unavailable') from error
    try:yield descriptor
    finally:os.close(descriptor)


@contextmanager
def _directory(root, phase, identity, *, create=False, exclusive=False):
    # Production runs on Linux. Never fall back to pathname checks on a host
    # lacking directory-relative no-follow operations.
    if (os.name!='posix' or not hasattr(os,'O_DIRECTORY') or not hasattr(os,'O_NOFOLLOW')
            or not {os.open,os.mkdir,os.rename}<=os.supports_dir_fd):
        raise PickFilesUnavailable('Safe directory-relative Pick IO is unavailable')
    names=(str(phase.run_id),'scope-pick',str(phase.pk),str(identity))
    with ExitStack() as stack:
        descriptor=os.open(root.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        stack.callback(os.close,descriptor)
        for name in root.parts[1:]:descriptor=stack.enter_context(_folder(descriptor,name))
        for index,name in enumerate(names):
            descriptor=stack.enter_context(_folder(descriptor,name,create=create,
                exclusive=exclusive and index==len(names)-1))
        yield descriptor


def _stream_metadata(stream):
    before=os.fstat(stream.fileno())
    if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:
        raise PickFilesUnavailable('Pick file must be a regular file with one link')
    checksum=hashlib.sha256();size=0
    while chunk:=stream.read(1024*1024):checksum.update(chunk);size+=len(chunk)
    after=os.fstat(stream.fileno())
    if (after.st_nlink!=1 or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=
            (after.st_size,after.st_mtime_ns,after.st_ctime_ns)):
        raise PickFilesUnavailable('Pick file changed during verification')
    return dict(size=size,sha256=checksum.hexdigest())


def _open(folder, name, *, write=False):
    flags=(os.O_WRONLY|os.O_CREAT|os.O_EXCL) if write else os.O_RDONLY
    try:descriptor=os.open(name,flags|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=folder)
    except OSError as error:raise PickFilesUnavailable('Required Pick file is absent or linked') from error
    stream=os.fdopen(descriptor,'wb' if write else 'rb')
    value=os.fstat(descriptor)
    if not stat.S_ISREG(value.st_mode) or value.st_nlink!=1:
        stream.close();raise PickFilesUnavailable('Pick file must be a regular file with one link')
    return stream


def _copy_file(output, download, name):
    with _open(output,name) as source,_open(download,name,write=True) as target:
        shutil.copyfileobj(source,target,length=1024*1024)
        target.flush();os.fsync(target.fileno())


def _write_candidate(state, directory):
    from mta.application.complete_daily_batch_files import PICK_NAMES,reports_from_pick_state,sqlcmd_chunks
    reports=reports_from_pick_state(state)
    with _folder(directory,'output',create=True) as output,_folder(directory,'download',create=True) as download:
        for kind,name in PICK_NAMES.items():
            with _open(output,name,write=True) as stream:
                for chunk in sqlcmd_chunks(reports[kind]['resultsets']):stream.write(chunk)
                stream.flush();os.fsync(stream.fileno())
            _copy_file(output,download,name)
        os.fsync(output);os.fsync(download)
    os.fsync(directory)


def _files(directory):
    from mta.application.complete_daily_batch_files import PICK_NAMES
    result={}
    for owner in ('output','download'):
        with _folder(directory,owner) as folder:
            if set(os.listdir(folder))!=set(PICK_NAMES.values()):
                raise PickFilesUnavailable('Exact four-file Pick roster required')
            for name in PICK_NAMES.values():
                with _open(folder,name) as stream:metadata=_stream_metadata(stream)
                if owner=='output':result[name]=metadata
                elif result[name]!=metadata:raise PickFilesUnavailable('Pick download copy differs')
    return result


def _identity(phase, recipe, directory, files):
    return dict(schema='fresh-scoped-pick-files-v1',phase_id=str(phase.pk),
        source_digest=phase.digest,snapshot_digest=phase.snapshot.state_digest,
        recipe_digest=recipe,directory=str(directory),files=files)


def read(phase_id, *, expected_digest):
    """Validate the entire bundle; DBM retains its exact BPR file owner."""
    from mta.runtime.models import ScopePickFiles
    phase,root=_binding(phase_id,expected_digest)
    receipt=ScopePickFiles.objects.filter(phase=phase).first()
    if receipt is None:raise PickFilesUnavailable('Accepted BPR Pick files are not prepared')
    identity=_identity(phase,receipt.recipe_digest,receipt.directory,receipt.files)
    if (receipt.source_digest!=phase.digest or not _compatible_recipe(receipt.recipe_digest)
            or receipt.digest!=digest(identity)):
        raise PickFilesUnavailable('Accepted BPR Pick file receipt differs')
    with _directory(root,phase,receipt.directory) as directory:
        if _files(directory)!=receipt.files:raise PickFilesUnavailable('Accepted BPR Pick file contents differ')
    return receipt


def prepare(phase_id, *, expected_digest, repair=False):
    """Prepare privately, then register. Repair only the same immutable bytes.

    A crash before registration leaves an unreferenced candidate. A retry uses
    the persisted phase; it never recaptures inputs or recalculates business work.
    Orphans are retained for explicit owned reconciliation, never selected.
    """
    from mta.runtime.models import ScopePickFiles,RunPhaseAcceptance
    from mta.runtime.scoped_actions import restore
    if type(repair) is not bool:raise ValueError('Explicit Pick repair boolean required')
    phase,root=_binding(phase_id,expected_digest)
    existing=ScopePickFiles.objects.filter(phase=phase).first()
    if existing is not None:
        try:return read(phase_id,expected_digest=expected_digest)
        except (PickFilesUnavailable,OSError):
            if not repair:raise
    value,_sources=restore(phase.run,phase)
    if value.pick_state is None:raise PickFilesUnavailable('Accepted BPR Pick state is absent')
    identity=uuid.uuid4()
    with _directory(root,phase,identity,create=True,exclusive=True) as candidate:
        _write_candidate(value.pick_state,candidate)
        files=_files(candidate)
    recipe=recipe_digest()
    with transaction.atomic():
        RunPhaseAcceptance.objects.select_for_update().get(pk=phase.pk)
        # Recheck the accepted owner after IO. No business source/queue is read.
        current,_root=_binding(phase.pk,phase.digest)
        existing=ScopePickFiles.objects.filter(phase=current).first()
        if existing is None:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.scope_pick_phase',%s,true)",[str(phase.pk)])
            receipt=ScopePickFiles.objects.create(phase=current,source_digest=current.digest,
                recipe_digest=recipe,directory=identity,files=files,
                digest=digest(_identity(current,recipe,identity,files)))
        else:
            if (existing.source_digest!=current.digest or not _compatible_recipe(existing.recipe_digest)
                    or existing.files!=files
                    or existing.digest!=digest(_identity(current,existing.recipe_digest,existing.directory,files))):
                raise PickFilesUnavailable('Repair cannot replace accepted Pick file contents')
            if repair:
                with _directory(root,current,existing.directory,create=True) as target, \
                        _directory(root,current,identity) as candidate:
                    for owner in ('output','download'):
                        with _folder(target,owner,create=True) as destination,_folder(candidate,owner) as source:
                            for name in files:
                                try:info=os.stat(name,dir_fd=destination,follow_symlinks=False)
                                except FileNotFoundError:info=None
                                if info is not None and (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1):
                                    raise PickFilesUnavailable('Pick repair target is linked or nonregular')
                                os.replace(name,name,src_dir_fd=source,dst_dir_fd=destination)
                            os.fsync(destination)
                    os.fsync(target)
            receipt=existing
    return read(phase_id,expected_digest=expected_digest)


def open_file(phase_id, name, *, expected_digest):
    """Return an already verified open download handle for an admitted caller."""
    from mta.application.complete_daily_batch_files import PICK_NAMES
    if name not in PICK_NAMES.values():raise PickFilesUnavailable('Unknown Pick download')
    receipt=read(phase_id,expected_digest=expected_digest)
    phase,root=_binding(phase_id,expected_digest)
    with _directory(root,phase,receipt.directory) as directory,_folder(directory,'download') as download:
        stream=_open(download,name)
    try:
        if _stream_metadata(stream)!=receipt.files[name]:
            raise PickFilesUnavailable('Pick download changed before opening')
        stream.seek(0)
        return stream
    except BaseException:
        stream.close();raise
