"""Freeze effective supplier/exclusion configuration and accepted-action ownership.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import migrations

# Frozen names; future runtime catalogue changes require another migration.
CONFIGURATION = ('mdmsupplierconfiguration','mdmsobraw','mdmmoqraw1','mdmmoqraw2',
    'mdmpairexclusionsource','mdmpairexclusion','mdmseasoneligibility')
FACT = ('mdmdailypairexclusion','mdmdailyinputtask','mdmdailyinputhistory',
    'mdmdailyskuarchive','mdmdailylocationarchive','mdmdailyskulocaddarchive',
    'mdmdailyskulocmodifyarchive','mdmdailyskulocremovearchive')
ACTION = ('mdmskuapproved','mdmlocationapproved','mdmskulocaddapproved',
    'mdmskulocmodifyapproved','mdmskulocremoveapproved','mdmsobapproved',
    'mdmmoqwithdestinationapproved','mdmmoqwithoutdestinationapproved',
    'mdmskuhistory','mdmlocationhistory','mdmskulochistory','mdmsobhistory',
    'mdmmoqhistory','mdmforcehistory','mdmseasonhistory','mdmseasonstatushistory',
    'mdmstoppipohistory','mdmphaseouthistory','mdmphaseinnormhistory',
    'mdmskuuploadlog','mdmlocationuploadlog','mdmskulocadduploadlog',
    'mdmskulocmodifyuploadlog','mdmskulocremoveuploadlog','mdmsobuploadlog',
    'mdmmoquploadlog','mdmforceuploadlog')


def install(apps, editor):
    q=editor.quote_name
    with editor.connection.cursor() as c:
        for kind,names in (('configuration',CONFIGURATION),('fact',FACT),('action',ACTION)):
            for name in names:
                table='mta.'+q('fresh_mta_'+name)
                for op,ref in (('INSERT','NEW TABLE AS new_rows'),
                        ('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
                        ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
                    trigger=q('ingestion_watch_'+op.lower())
                    c.execute('DROP TRIGGER '+trigger+' ON '+table)
                    c.execute('CREATE TRIGGER '+trigger+' AFTER '+op+' ON '+table+
                        (' REFERENCING '+ref if ref else '')+
                        ' FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch(%s)',[kind])


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0146_ingestion_revision_state')]
    operations=[migrations.RunPython(install)]
