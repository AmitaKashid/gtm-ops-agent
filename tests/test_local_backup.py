import subprocess

import pytest

from workspace_db.backup_local import backup, verify_restore


def test_backup_never_overwrites_existing_file(tmp_path):
    target = tmp_path / 'backup.dump'
    target.write_bytes(b'existing')
    with pytest.raises(FileExistsError):
        backup(target)
    assert target.read_bytes() == b'existing'


def test_failed_backup_removes_partial_file(tmp_path, monkeypatch):
    target = tmp_path / 'backup.dump'
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        backup(target)
    assert not target.exists()


def test_restore_uses_generated_database_and_cleans_up(tmp_path, monkeypatch):
    target = tmp_path / 'backup.dump'
    target.write_bytes(b'archive')
    calls = []
    monkeypatch.setattr(subprocess, 'run', lambda args, **kwargs: calls.append(args))
    name = verify_restore(target)
    assert name.startswith('gtm_restore_check_') and name != 'gtmops'
    assert any('pg_restore' in cmd and name in cmd for cmd in calls)
    assert calls[-1][-1] == name and 'dropdb' in calls[-1]


def test_restore_failure_still_removes_temporary_database(tmp_path, monkeypatch):
    target = tmp_path / 'backup.dump'
    target.write_bytes(b'archive')
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if 'pg_restore' in args:
            raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(subprocess, 'run', run)
    with pytest.raises(subprocess.CalledProcessError):
        verify_restore(target)
    assert 'dropdb' in calls[-1]
