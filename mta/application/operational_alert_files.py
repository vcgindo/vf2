"""Native attachment projections over explicit O7 producer populations."""
from mta.application.operational_sqlcmd import scalar,resultset_bytes,_bytes
from mta.domain.complete_daily_scalars import parse_datetime

SOURCES={
    'invalid':('Scripts/Importer/InvalidDataReport.sql','26011ea60891f9f04156f7bcac77080015c2f957c81cedb5c612aed72b24874e'),
    'unavailable':('Scripts/Importer/DailyDataUnavailabilityReport.sql','34fa806c9978c8b36818962be0ea03bb75fcfa1a4d44b248e61edc50991e3a16'),
    'phase':('Scripts/DBM/Misc/GeneratePhaseInPhaseOutExceptionReport.sql','0d8435f3276fa3209ef5a255083ed121fea84a4c46d06bab9e42c84d1128fa9e'),
    'force':('Scripts/DBM/Misc/FailedForceNormChange.sql','6446f1445c89a3859234f6ea5a03eada4a97695daeeae8282a4e5747a8ca7c1a'),
}


def _same_time(value,clock):
    return value is not None and parse_datetime(value)==parse_datetime(clock)


def _report(header,kinds,rows):
    return resultset_bytes([dict(fields=header,types=['varchar-literal']*len(header),rows=[header]),
                            dict(fields=header,types=kinds,rows=rows)])


def invalid_data_bytes(rejected,clock):
    selected=[row for row in rejected if _same_time(row['RejectionDate'],clock)]
    selected.sort(key=lambda row:row['ReasonCode'],reverse=True)
    return _report(['SKUCode','WarehouseCode','RunDatetime','ReasonDescription'],
        ['nvarchar(50)','nvarchar(50)','datetime','nvarchar(100)'],
        [[row[name] for name in ('SKUCode','WhCode','RejectionDate','ReasonDescription')] for row in selected])


def unavailable_daily_bytes(reasons,clock):
    return _report(['RunDateTime','Reason'],['datetime','nvarchar(512)'],
        [[row['RunDateTime'],row['Reason']] for row in reasons if _same_time(row['RunDateTime'],clock)])


def phase_exception_bytes(report_rows):
    """Read the already selected Reports.controls phase projection verbatim."""
    fields=('PhaseOutSKUCode','WhCode','PhaseInSKUCode','TargetNorm','Reason','Date')
    if any(set(row)!=set(fields) for row in report_rows):
        raise ValueError('Exact persisted phase exception projection required')
    return _report(list(fields),['nvarchar(50)','nvarchar(50)','nvarchar(50)',
        'nvarchar(10)','nvarchar(200)','datetime'],[[row[name] for name in fields] for row in report_rows])


def failed_force_bytes(report_rows):
    """This one native wrapper omits -W: retain SQLCMD's fixed field padding."""
    fields=('SKUCode','WhCode','VectorFlowNorm','Reason')
    if any(set(row)!=set(fields) for row in report_rows):
        raise ValueError('Exact persisted failed force projection required')
    lines=['SKUCode,WHCode,VectorFlowNorm,Reason\r\n']
    # Native display width is max(type width, column alias width). The alias
    # VectorFlowNorm is fourteen characters although CONVERT is varchar(10).
    widths=(50,50,14,250)
    kinds=('nvarchar(50)','nvarchar(50)','varchar(10)','nvarchar(250)')
    for row in report_rows:
        lines.append(','.join(scalar(row[name],kind).ljust(width)
            for name,kind,width in zip(fields,kinds,widths,strict=True))+'\r\n')
    return _bytes(''.join(lines))
