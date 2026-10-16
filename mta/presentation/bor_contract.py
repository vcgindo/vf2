"""Exact April BOR snapshot boundary; not a modern calculation publication."""
RUN_ID = 'bfd75b4b-a9df-4a08-82d3-852e3324b623'
BUSINESS_DATE = '2026-04-07'
NATIVE_DIGEST = '4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73'
MANIFEST_DIGEST = 'afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836'
BACKUP_DIGEST = 'c15dc63dbbd6161cb6c540673829c373a550a10b2ec65e43198757e7fa396747'

# Native field order is part of the retained full-value capture checksum.
KEYS = {'SKUCode': 'text50', 'WHCode': 'text50', 'SupplierCode': 'text50'}
FIELDS = {
    'SupplierDispatchReq': {
        **KEYS, **{n: 'int' for n in ('OriginalReq', 'DispatchReq', 'ReqTopOfRed',
            'ReqTopOfYellow', 'ReqTopOfGreen', 'ReqTopOfBlue')},
        **{f'SKULocAtt{i:02}': 'nullable50' for i in range(1, 16)},
        **{n: 'int' for n in ('CumulativeTOR', 'CumulativeTOY', 'CumulativeTOG',
            'CumulativeTOB', 'ReqTopOfBlack', 'CumulativeTOBlack')}},
    'SOBData': {**KEYS, 'SOB': 'float'},
    'MOQData': {**KEYS, 'MOQ': 'int'},
    'BORReport_RemarkDetails': {'SKUCode': 'text50', 'WhCode': 'text50',
        'Remark': 'nullable_text', 'Username': 'nullable100', 'RemarkDate': 'datetime',
        'SupplierCode': 'text50'},
}
PINS = {
    'SupplierDispatchReq': (1196, 'a1c2cddf64fafd6551cac3cca2f9907d46ad7b40d243dc5de746f6d0b4dab986'),
    'SOBData': (97, '79daf15208d605d237a6a6209ae57c040694969d6b266c9342829342ab5ba28e'),
    'MOQData': (1496, 'e1414c332ef6adeb197ce27482c12ab24dd9073de4dc72c880a8aa43b695b271'),
    'BORReport_RemarkDetails': (27, '6db50d13153f459d7925bf5ddd394a1082389d02906eb64b40874729f162c151'),
}


def recipe_digest():
    from mta.serialization import digest
    return digest(dict(version=1, run=RUN_ID, date=BUSINESS_DATE, native=NATIVE_DIGEST,
                       manifest=MANIFEST_DIGEST, backup=BACKUP_DIGEST, fields=FIELDS, pins=PINS))


def production_recipe_digest():
    from mta.serialization import digest
    return digest(dict(schema='fresh-bor-source-schema-v1', fields=FIELDS))
