from mta.presentation.native_mode import removed_mode
"""Bounded opt-in read delivery cache, keyed after access/publication validation."""
from collections import OrderedDict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import threading
import time

from mta.serialization import digest


class ReportReadCache:
    def __init__(self, max_bytes=16 * 1024 * 1024, max_entries=64, ttl=300):
        self.max_bytes, self.max_entries, self.ttl = max_bytes,max_entries,ttl
        self.entries, self.running, self.bytes = OrderedDict(),set(),0
        self.condition = threading.Condition()

    def get_or_compute(self,key,compute):
        with self.condition:
            while True:
                entry = self.entries.get(key)
                if entry:
                    expires,content = entry
                    if expires > time.monotonic():
                        self.entries.move_to_end(key); return content
                    self.bytes -= len(content); del self.entries[key]
                if key not in self.running:
                    self.running.add(key); break
                self.condition.wait()
        try:
            content = compute()
            if content is not None and len(content) <= self.max_bytes:
                with self.condition:
                    self.entries[key] = (time.monotonic()+self.ttl,content); self.bytes += len(content)
                    while self.bytes > self.max_bytes or len(self.entries) > self.max_entries:
                        _,(_,value) = self.entries.popitem(last=False); self.bytes -= len(value)
            return content
        finally:
            with self.condition:
                self.running.discard(key); self.condition.notify_all()


cache = ReportReadCache()


@lru_cache(maxsize=1)
def reader_recipe():
    root = Path(__file__).resolve().parent
    files = ('views.py', 'report_cache.py', 'insight_read.py', 'insight_filters.py', 'insight_response.py', 'guided_aggregates.py', 'guided_history_prepared.py', 'insight_history_sql.py', 'guided_dbm.py', 'guided_chronic.py', 'chronic_sql.py', 'context.py', 'permissions.py',
        'scoped_guided.py', 'scoped_guided_dbm.py', 'scoped_guided_chronic.py',
        'scoped_guided_availability.py', 'scoped_guided_excess.py', 'registered_report_view.py')
    return digest({name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files})


def read_identity(run, payload, actor, *, read_binding=None):
    from mta.presentation.context import PublicationUnavailable
    if read_binding is not None:
        from mta.presentation.scoped_guided import GuidedBinding
        if not isinstance(read_binding,GuidedBinding) or read_binding.run.pk!=run.pk:
            raise PublicationUnavailable('scoped_guided_read_binding_differs')
        return digest(dict(binding=read_binding.identity(payload,actor),recipe=reader_recipe()))
    from mta.presentation.guided_aggregates import recipe_digest, source_binding
    from mta.runtime.models import ReportAggregateReceipt
    from mta.presentation.native_publication import enabled
    if not (enabled() and run.kind == 'DAILY_CHAIN'):
        raise PublicationUnavailable('report_read_cache_publication_required')
    source = source_binding(run)
    receipt = ReportAggregateReceipt.objects.filter(run=run).first()
    if receipt is None or receipt.source_digest != source or receipt.recipe_digest != recipe_digest():
        raise PublicationUnavailable('report_read_aggregate_generation_unavailable')
    from mta.runtime.report_aggregate_schema import verify_guards
    from django.db import connection
    verify_guards(connection)
    from mta.runtime import guided_history_schema, guided_dbm_schema, guided_chronic_schema
    from mta.runtime.models import GuidedHistoryPreparedProjection, GuidedDbmPreparedProjection, GuidedChronicPreparedProjection
    for module in (guided_history_schema, guided_dbm_schema, guided_chronic_schema):
        try:
            module.verify_guards(connection)
        except ValueError as exc:
            raise PublicationUnavailable('report_read_source_guards_changed') from exc
    sources = {}
    for model in (GuidedHistoryPreparedProjection, GuidedDbmPreparedProjection, GuidedChronicPreparedProjection):
        fields = [field.attname for field in model._meta.fields if field.name not in ('id', 'run', 'created_at')]
        sources[model.__name__] = list(model.objects.filter(run=run).order_by('pk').values(*fields))
    scope = {key: payload.get(key, []) for key in ('product_permissions', 'location_permissions')}
    return digest(dict(run=str(run.pk), source=source, aggregates=receipt.rows_digest, memberships=receipt.members_digest, prepared=sources, recipe=reader_recipe(), scope=scope, actor=actor))


def cached_response(request, payload, kind, compute, *, read_binding=None):
    from django.http import HttpResponse, JsonResponse
    from mta.presentation.context import selected_run, PublicationUnavailable
    from mta.presentation.views import identity
    from mta.runtime.models import ReportAggregateReceipt
    run = selected_run() if read_binding is None else read_binding.run
    claimed = payload.pop('_report_read_identity', None)
    from mta.presentation.native_publication import enabled
    eligible = read_binding is not None or (enabled() and run.kind == 'DAILY_CHAIN')
    if not eligible or (read_binding is None and not ReportAggregateReceipt.objects.filter(run=run).exists()):
        if claimed is not None:
            raise PublicationUnavailable('report_read_generation_unavailable')
        return compute()
    token = read_identity(run, payload, identity(request), read_binding=read_binding)
    if claimed is not None and claimed != token:
        return JsonResponse({'error': 'report_read_identity_changed'}, status=409)
    key = digest(dict(identity=token, kind=kind, payload=payload))
    response = None

    def load():
        nonlocal response
        response = compute()
        if response.status_code != 200 or response.streaming:
            return None
        try:
            body = json.loads(response.content)
        except (ValueError, TypeError):
            return None
        return bytes(response.content) if body.get('status') == 200 else None
    content = cache.get_or_compute(key, load)
    if content is None:
        return response
    result = HttpResponse(content, content_type='application/json')
    result['Cache-Control'] = 'private, no-store'
    return result
