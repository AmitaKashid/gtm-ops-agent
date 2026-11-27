import pytest
from workspace_db.bootstrap_local import validate_environment


def test_bootstrap_restricts_environment_and_database_host():
    validate_environment('postgresql://dev:pass@127.0.0.1:5432/local', 'development', '')
    for url, env, demo in [
        ('postgresql://dev:pass@db.example/prod', 'development', ''),
        ('postgresql://dev:pass@localhost/test?host=db.example', 'development', ''),
        ('postgresql://dev:pass@localhost/test', 'production', ''),
        ('postgresql://dev:pass@localhost/test', 'development', 'true'),
    ]:
        with pytest.raises(RuntimeError):
            validate_environment(url, env, demo)
