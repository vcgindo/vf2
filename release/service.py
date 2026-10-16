"""Start a migrated service. Restarts never install schemas, inputs, users or capabilities."""
import argparse
import os
from release.configuration import integer


def command(service):
    if service == 'mta':
        return ['gunicorn', 'vectorflow.wsgi:application', '--preload', '--bind', '0.0.0.0:8000',
            '--workers', str(integer('MTA_WORKERS', 2, maximum=4)),
            '--timeout', str(integer('MTA_TIMEOUT', 180, maximum=3600)),
            '--graceful-timeout', str(integer('MTA_GRACEFUL_TIMEOUT', 30, maximum=300)),
            '--access-logfile', '-', '--error-logfile', '-']
    if service == 'auth':
        return ['uvicorn', 'apps.asgi:application', '--host', '0.0.0.0', '--port', '10016',
            '--workers', str(integer('AUTH_WORKERS', 1, maximum=4)),
            '--timeout-keep-alive', str(integer('AUTH_KEEP_ALIVE', 5, maximum=300))]
    if service == 'mto':
        return ['daphne', '-b', '0.0.0.0', '-p', '10015',
            '--http-timeout', str(integer('MTO_HTTP_TIMEOUT', 180, maximum=3600)),
            '--websocket_connect_timeout', str(integer('MTO_WEBSOCKET_CONNECT_TIMEOUT', 30, maximum=300)),
            '--ping-interval', str(integer('MTO_WEBSOCKET_PING_INTERVAL', 20, maximum=300)),
            '--ping-timeout', str(integer('MTO_WEBSOCKET_PING_TIMEOUT', 30, maximum=300)),
            'MTO_API.asgi:application']
    raise ValueError('Unknown service')


def check_migrations():
    import django
    django.setup()
    from django.db import connection, transaction
    from django.db.migrations.executor import MigrationExecutor
    from django.core.checks import run_checks, ERROR
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION READ ONLY')
            cursor.execute('SELECT 1')
        executor = MigrationExecutor(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            raise ValueError('Pending service migrations: run the explicit installation/upgrade command')
        transaction.set_rollback(True)
    if any(problem.level >= ERROR for problem in run_checks()):
        raise ValueError('Service Django configuration check failed')
    connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service', choices=('mta', 'mto', 'auth'))
    service = parser.parse_args().service
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.' + service + '_settings')
    args = command(service)
    check_migrations()
    os.execvp(args[0], args)
