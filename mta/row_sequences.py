"""Immutable reiterable history rows with bounded-heap ordinal access.

PostgreSQL remains operational truth. The private temporary spool is an
execution cache, never an opening, a persisted state payload or an oracle.
Each read returns a sealed row; explicitly copying a row gives a mutable row.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from collections.abc import Sequence
from collections import OrderedDict
from array import array
from copy import deepcopy
from datetime import date,datetime
from decimal import Decimal
import hashlib
import json
import mmap
import os
from pathlib import Path
import struct
import tempfile
from threading import local
import weakref
import zlib


def _cache_row(row):
    # The execution cache preserves Python scalar kinds as well as wire values.
    # Decimal/date are strings on the canonical wire, but remain typed here.
    result=[]
    for key,value in row.items():
        kind=('decimal' if isinstance(value,Decimal) else 'datetime' if isinstance(value,datetime)
            else 'date' if isinstance(value,date) else 'scalar')
        result.append([key,kind,str(value) if kind=='decimal' else value.isoformat() if kind in ('date','datetime') else value])
    return json.dumps(result,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()


def _read_cache(raw):
    return {key:(Decimal(value) if kind=='decimal' else datetime.fromisoformat(value) if kind=='datetime'
        else date.fromisoformat(value) if kind=='date' else value) for key,kind,value in json.loads(raw)}


class ReadOnlyRow(dict):
    def _sealed(self,*args,**kwargs):
        raise TypeError('Immutable history row; create a transformed generation')
    __setitem__=__delitem__=clear=pop=popitem=setdefault=update=__ior__=_sealed

    def __deepcopy__(self,memo):
        return {key:deepcopy(value,memo) for key,value in self.items()}


class RecordRows(Sequence):
    """Closed immutable record protocol; factories must yield isolated rows."""
    def __init__(self,count,factory,*,getitem=None):
        if type(count) is not int or count<0:raise ValueError('Explicit row count required')
        self.count,self.factory,self._getter=count,factory,getitem
        self._ordinal_cache=None

    @classmethod
    def from_rows(cls,rows):
        """Spool one generation, retaining all canonical values and ordinals."""
        from mta.serialization import canonical_parts
        base=os.environ.get('VF_WORK_ROOT')
        if base:Path(base).mkdir(parents=True,exist_ok=True)
        directory=tempfile.TemporaryDirectory(prefix='fresh-history-',dir=base)
        try:
            data=Path(directory.name)/'rows';offsets=Path(directory.name)/'ordinals'
            checksum=hashlib.sha256(b'[');physical=hashlib.sha256();count=0;fields=None
            block=[];block_digests=bytearray();block_sizes=array('I')
            def flush(output,index):
                if not block:return
                compressed=zlib.compress(b''.join(block),level=1)
                raw=struct.pack('<I',len(compressed))+compressed
                index.write(struct.pack('<Q',output.tell()))
                output.write(raw);physical.update(raw);block_digests.extend(hashlib.sha256(raw).digest());block_sizes.append(len(compressed));block.clear()
            with data.open('wb') as output,offsets.open('wb') as index:
                for row in rows:
                    if not isinstance(row,dict) or any(not isinstance(k,str) for k in row):
                        raise ValueError('History cache requires declared record rows')
                    if any(isinstance(v,(dict,list,tuple,RecordRows)) for v in row.values()):
                        raise ValueError('History cache records must be flat')
                    if fields is None:fields=frozenset(row)
                    if frozenset(row)!=fields:raise ValueError('History row roster differs')
                    raw=_cache_row(row);logical=b''.join(canonical_parts(row))
                    block.append(raw+b'\n')
                    if len(block)==256:flush(output,index)
                    if count:checksum.update(b',')
                    checksum.update(logical);count+=1
                flush(output,index)
            checksum.update(b']')
            result=cls(count,lambda:())
            result._directory=directory;result._data=data;result._offsets=offsets
            result._digest=checksum.hexdigest();result._fields=fields
            result._cache_digest=physical.hexdigest();result._block_digests=bytes(block_digests);result._block_sizes=block_sizes
            result._data_stat=result._identity(data);result._index_stat=result._identity(offsets)
            result._thread=local()
            reference=weakref.ref(result)
            result.factory=lambda:reference()._iterate_spool()
            result._getter=lambda ordinal:reference()._get_spooled(ordinal)
            return result
        except BaseException:
            directory.cleanup();raise

    @staticmethod
    def _identity(path):
        info=path.stat();return info.st_size,info.st_mtime_ns

    def _check_spool(self):
        if self._identity(self._data)!=self._data_stat or self._identity(self._offsets)!=self._index_stat:
            raise ValueError('Private history execution cache changed')

    def _iterate_spool(self):
        self._check_spool();checksum=hashlib.sha256();count=0;block=0
        with self._data.open('rb') as stream:
            while header:=stream.read(4):
                if len(header)!=4:raise ValueError('Incomplete history cache block')
                if block>=len(self._block_sizes) or struct.unpack('<I',header)[0]!=self._block_sizes[block]:
                    raise ValueError('History cache block size drift')
                raw=stream.read(self._block_sizes[block])
                if hashlib.sha256(header+raw).digest()!=self._block_digests[block*32:(block+1)*32]:
                    raise ValueError('History cache block value/order drift')
                checksum.update(header+raw);block+=1
                for line in zlib.decompress(raw).splitlines():
                    count+=1
                    yield _read_cache(line)
        self._check_spool()
        if count!=self.count or checksum.hexdigest()!=self._cache_digest:
            raise ValueError('History execution-cache value/order/count drift')

    def _get_spooled(self,index):
        self._check_spool()
        if not hasattr(self._thread,'data'):
            self._thread.data=self._data.open('rb')
            self._thread.index=self._offsets.open('rb')
            self._thread.mapping=mmap.mmap(self._thread.index.fileno(),0,access=mmap.ACCESS_READ)
            self._thread.blocks=OrderedDict()
        block,ordinal=divmod(index,256)
        if block not in self._thread.blocks:
            position=struct.unpack_from('<Q',self._thread.mapping,block*8)[0]
            self._thread.data.seek(position);header=self._thread.data.read(4)
            if len(header)!=4:raise ValueError('Incomplete history ordinal block')
            if struct.unpack('<I',header)[0]!=self._block_sizes[block]:
                raise ValueError('History ordinal block size drift')
            raw=self._thread.data.read(self._block_sizes[block])
            if hashlib.sha256(header+raw).digest()!=self._block_digests[block*32:(block+1)*32]:
                raise ValueError('History ordinal block value/order drift')
            self._thread.blocks[block]=zlib.decompress(raw).splitlines()
            # Bounded compressed-block read cache; never a whole history graph.
            if len(self._thread.blocks)>8:self._thread.blocks.popitem(last=False)
        lines=self._thread.blocks[block]
        if ordinal>=len(lines):raise ValueError('Incomplete history ordinal')
        self._thread.blocks.move_to_end(block)
        self._check_spool()
        return _read_cache(lines[ordinal])

    def __len__(self):return self.count

    def __iter__(self):
        count=0
        for row in self.factory():
            if not isinstance(row,dict):raise ValueError('History factory must retain records')
            count+=1;yield ReadOnlyRow(row)
        if count!=self.count:raise ValueError('History factory population drift')

    def __getitem__(self,index):
        if isinstance(index,slice):
            positions=range(*index.indices(self.count))
            return RecordRows(len(positions),lambda:(self[i] for i in positions))
        if not isinstance(index,int):raise TypeError('History ordinal must be integer')
        if index<0:index+=self.count
        if not 0<=index<self.count:raise IndexError(index)
        if self._getter is not None:return ReadOnlyRow(self._getter(index))
        for ordinal,row in enumerate(self):
            if ordinal==index:return row
        raise IndexError(index)

    def __deepcopy__(self,memo):return self

    def __eq__(self,other):
        if not isinstance(other,(list,tuple,RecordRows)) or len(self)!=len(other):return False
        return all(left==right for left,right in zip(self,other))

    def ordinal_source(self):
        """One execution-local cache for repeated pair→ordinal consumers."""
        if hasattr(self,'_data'):return self
        if self._ordinal_cache is None:self._ordinal_cache=RecordRows.from_rows(self)
        return self._ordinal_cache

    def __del__(self):
        # Windows requires mappings/handles closed before directory removal.
        state=getattr(self,'_thread',None)
        if state is not None:
            for name in ('mapping','data','index'):
                value=getattr(state,name,None)
                if value is not None:value.close()
        directory=getattr(self,'_directory',None)
        if directory is not None:directory.cleanup()


def is_record_rows(value):return isinstance(value,(list,RecordRows))


def history_rows(rows,*,like):
    return RecordRows.from_rows(rows) if isinstance(like,RecordRows) else list(rows)
