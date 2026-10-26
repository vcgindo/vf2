"""Actual bounded DataFiles check for the pre-import diagnostic boundary.

No hook execution, substitution, GoAhead deletion or implicit configuration.
The runtime caller owns registration, immutable persistence and publication.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import os
import re

from mta.application.production_csv_files import contained, regular
from mta.domain import complete_daily_fullkit as native
from mta.domain.complete_daily_scalars import ascii_equal, parse_datetime


POLICY='fresh-literal-datafiles-fullkit-v1'
HOOKS=('PreDataAvailabilityCheckProcessing.bat','CheckGoAhead.bat',
       'CheckDailyDataAvailabilityFromDatabase.bat')
CRITICAL_FIELDS={'Id','Path','FileName','Type','Exists','ResolvedPath','ResolvedFileName'}
SOURCES={
    'Engine/CheckRunStartCriteria.bat':'9edf97b4a08b095bb97380576e5616cd84efa725ae37ed13e63b28974c4101ce',
    'Engine/CheckForFilesAvailability.bat':'98b9a3aec5dffdf2168943c6db79922d366b7b853fdda19595a79fceacfbce53',
    'Scripts/Importer/GetUnavailableFiles.sql':'d71c18293294f52c529ce6a02232eec48b78fb091e830b5cd5a407a4ff674601',
}


def _text(value,width,*,nullable=False):
    if value is None and nullable:return
    if type(value) is not str or width is not None and len(value.encode('utf-16-le'))//2>width:
        raise ValueError('Native fullkit text contract differs')


def _integer(value):
    if type(value) is not int or not -(2**31)<=value<2**31:
        raise ValueError('Native fullkit SQL int required')


def _literal(path,name,input_root):
    # CALL SET and delayed expansion belong to the original batch language.
    # Admit only values for which no interpretation is necessary.
    if (not path or any(char in path for char in '%!\"\'\r\n,\x00&|<>^')
            or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*',name)
            or name in ('.','..') or name.endswith('.')):
        raise ValueError('Only literal safe DataFiles paths and names are qualified')
    directory=Path(path)
    if not directory.is_absolute() or '..' in directory.parts:
        raise ValueError('Explicit absolute literal DataFiles path required')
    return contained(directory/name,input_root)


def configuration(*,critical_files,settings,abort_opening,input_root,site_root):
    """Qualify only the declared rows; never invent missing settings/history."""
    input_root=contained(input_root,input_root)
    site_root=contained(site_root,site_root)
    if not input_root.is_dir() or not site_root.is_dir():
        raise ValueError('Existing owned input and site roots required')
    if not isinstance(critical_files,list) or not isinstance(settings,list) or not isinstance(abort_opening,list):
        raise ValueError('Explicit ordered fullkit populations required')
    seen=set()
    for row in critical_files:
        if not isinstance(row,dict) or set(row)!=CRITICAL_FIELDS:
            raise ValueError('Exact native CriticalFiles columns required')
        _integer(row['Id'])
        if row['Id'] in seen:raise ValueError('Native CriticalFiles primary key differs')
        seen.add(row['Id'])
        for field,width in (('Path',150),('FileName',100),('Type',20)):_text(row[field],width)
        _text(row['ResolvedPath'],150,nullable=True)
        _text(row['ResolvedFileName'],100,nullable=True)
        if type(row['Exists']) is not bool:raise ValueError('Native CriticalFiles bit required')
        if not ascii_equal(row['Type'],'DataFiles'):
            raise ValueError('Only DataFiles are qualified; GoAhead semantics are not inferred')
        _literal(row['Path'],row['FileName'],input_root)
    for row in settings:
        if not isinstance(row,dict) or set(row)!={'Parameter','Value'}:
            raise ValueError('Exact fullkit settings columns required')
        _text(row['Parameter'],50);_text(row['Value'],None)
    for row in abort_opening:
        if not isinstance(row,dict) or set(row)!={'FileId','RunDateTime','Reason'}:
            raise ValueError('Exact native abort history columns required')
        _integer(row['FileId']);parse_datetime(row['RunDateTime']);_text(row['Reason'],512)
    # Explicit absence is observed, not a synthetic success result from a hook.
    for name in HOOKS:
        candidate=contained(site_root/name,site_root)
        if candidate.exists():raise ValueError('Site fullkit hooks are outside this literal boundary')
    return dict(policy=POLICY,input_root=str(input_root),site_root=str(site_root),
        CriticalFiles=deepcopy(critical_files),ImporterSettingsTbl=deepcopy(settings),
        RunAbortReasons=deepcopy(abort_opening),absent_hooks=list(HOOKS))


def _capture(path,destination,input_root):
    """Freeze a present member once, retaining the complete bytes and hash."""
    path=regular(path,input_root)
    before=path.stat()
    checksum=sha256();size=0
    with path.open('rb') as source,destination.open('xb') as target:
        for block in iter(lambda:source.read(1024*1024),b''):
            checksum.update(block);size+=len(block);target.write(block)
        target.flush();os.fsync(target.fileno())
    after=regular(path,input_root).stat()
    if ((before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino)
            or size!=before.st_size):
        raise ValueError('DataFiles changed during fullkit capture')
    return dict(sha256=checksum.hexdigest(),size_bytes=size)


def check(config,*,business_date,run_datetime,capture_root):
    """Check real inputs and return native outcome plus original observations.

    capture_root must be a new private directory. Failure leaves partial
    evidence in place. Only the caller may seal/publish a completed outcome.
    """
    if (not isinstance(config,dict) or set(config)!={'policy','input_root','site_root',
            'CriticalFiles','ImporterSettingsTbl','RunAbortReasons','absent_hooks'}
            or config['policy']!=POLICY or config['absent_hooks']!=list(HOOKS)):
        raise ValueError('Exact declared literal fullkit configuration required')
    actual=configuration(critical_files=config['CriticalFiles'],settings=config['ImporterSettingsTbl'],
        abort_opening=config['RunAbortReasons'],input_root=config['input_root'],site_root=config['site_root'])
    if actual!=config:raise ValueError('Literal fullkit configuration normalization differs')
    clock=parse_datetime(run_datetime)
    if clock.tzinfo is not None or clock.date().isoformat()!=business_date:
        raise ValueError('Explicit native local clock on the declared business date required')
    root=contained(capture_root,capture_root)
    source_root=Path(config['input_root'])
    if root.is_relative_to(source_root) or source_root.is_relative_to(root):
        raise ValueError('Fullkit custody must be separate from original input root')
    root.mkdir(parents=False,exist_ok=False)
    state=native.initialise_fullkit(config['ImporterSettingsTbl'],config['CriticalFiles'],business_date,equal=ascii_equal)
    observations=[]
    for ordinal,row in enumerate(state['CriticalFiles']):
        path=_literal(row['Path'],row['FileName'],source_root)
        row.update(ResolvedPath=row['Path'],ResolvedFileName=row['FileName'])
        # Existing directories and unsafe files are not treated as missing data.
        # This boundary admits regular data files only; preserve honest refusal.
        exists=path.exists()
        item=dict(ordinal=ordinal,file_id=row['Id'],path=str(path),exists=exists,
            member=None,sha256=None,size_bytes=None)
        if exists:
            item['member']=f'{ordinal:08d}-{row["FileName"]}'
            item.update(_capture(path,root/item['member'],source_root))
        elif path.exists():
            raise ValueError('DataFiles appeared during missing-file observation')
        row['Exists']=exists;observations.append(item)
    # No GoAheadFiles and no hooks were admitted. These are the BAT's explicit
    # initial values, not invented site-check results.
    go=native.file_availability(state['CriticalFiles'],'GoAheadFiles',previous=True,equal=ascii_equal)
    files=native.file_availability(state['CriticalFiles'],'DataFiles',previous=go['files_available'],equal=ascii_equal)
    reasons=native.unavailable_file_reasons(config['RunAbortReasons'],state['CriticalFiles'],
        'DataFiles',run_datetime,equal=ascii_equal)
    outcome=native.fullkit_outcome(state['ImporterSettingsTbl'],go_ahead=True,
        files_available=files['files_available'],daily_data_available=True,equal=ascii_equal)
    # A final observation refuses a changing input boundary. Accepted originals
    # stay in capture_root; later runtime consumption must use its own snapshot.
    for item in observations:
        if _literal(config['CriticalFiles'][item['ordinal']]['Path'],
                    config['CriticalFiles'][item['ordinal']]['FileName'],source_root).exists()!=item['exists']:
            raise ValueError('DataFiles existence changed during fullkit check')
    configuration(critical_files=config['CriticalFiles'],settings=config['ImporterSettingsTbl'],
        abort_opening=config['RunAbortReasons'],input_root=config['input_root'],site_root=config['site_root'])
    return dict(policy=POLICY,clock=clock.isoformat(timespec='milliseconds'),
        business_date=business_date,CriticalFiles=state['CriticalFiles'],
        RunAbortReasons=reasons,observations=observations,**outcome)
