"""Create and verify backups of the local Compose development database only.

This utility is not an automated production backup system.
"""
import argparse
from pathlib import Path
import subprocess
from uuid import uuid4


COMPOSE = ('docker', 'compose', 'exec', '-T', 'postgres')


def backup(output: Path):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open('xb') as stream:
            try:
                output.chmod(0o600)
                subprocess.run([*COMPOSE, 'pg_dump', '-U', 'gtmuser', '-d', 'gtmops', '-Fc'], stdout=stream, check=True)
            except BaseException:
                stream.close()
                output.unlink(missing_ok=True)
                raise
    except FileExistsError:
        raise FileExistsError('Backup already exists; choose a new filename') from None
    return output


def verify_restore(archive: Path):
    archive = Path(archive)
    if not archive.is_file():
        raise FileNotFoundError('Backup archive not found')
    # A random throwaway name cannot collide with the normal development DB.
    database = 'gtm_restore_check_' + uuid4().hex
    created = False
    try:
        subprocess.run([*COMPOSE, 'createdb', '-U', 'gtmuser', database], check=True)
        created = True
        with archive.open('rb') as source:
            subprocess.run([*COMPOSE, 'pg_restore', '-U', 'gtmuser', '-d', database,
                            '--no-owner', '--no-privileges', '--exit-on-error'], stdin=source, check=True)
        subprocess.run([*COMPOSE, 'psql', '-U', 'gtmuser', '-d', database,
                        '-v', 'ON_ERROR_STOP=1', '-c',
                        'SELECT count(*) AS applied_workspace_migrations FROM workspace_schema_migrations'], check=True)
    finally:
        if created:
            subprocess.run([*COMPOSE, 'dropdb', '-U', 'gtmuser', '--if-exists', database], check=True)
    return database


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    make = sub.add_parser('backup')
    make.add_argument('--output', type=Path, required=True)
    verify = sub.add_parser('verify')
    verify.add_argument('--file', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'backup':
        backup(args.output)
        print('Local backup created.')
    else:
        verify_restore(args.file)
        print('Restore verification completed in a temporary database.')


if __name__ == '__main__':
    main()
