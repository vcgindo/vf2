"""Install retained synthetic master owners once in the exclusively owned shell.

Importer/DBM/BTR bags come from their registered opening JSON paths. The BPR
metadata owner uses the canonical 01.ImportData full-copy statements. No engine
outputs, old workflows, credentials or April fixture rows are imported.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from django.db import connection, transaction

from mta.mdm.daily_source import (SCHEMA, ARTIFACT_SHA, APPROVAL_DAY_ARTIFACT_SHA,
                                  adapter_digest, configuration_digest, require_binding)
from mta.mdm.owned_namespace import authorize_install
from mta.mdm.source import DLL
from mta.runtime import mdm_models as models
from mta.runtime import mdm_skuloc_models as pairs
from mta.serialization import digest, storage

BPR_COPY_SHA = 'c248baeedda13d74a71a499c8b59b7ec46f05f11db00938de59a746bce94ce93'
IL_SHA = 'ccd47dc8d76895a6aa63ad5d6beaadb32f4f53ab75047a68fb8055382fd87ca1'




from mta.mdm.master_owners import business_fields, typed, owner_batches


def owners(artifact):
    return owner_batches(artifact['case']['opening'])
