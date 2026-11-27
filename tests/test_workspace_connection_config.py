from urllib.parse import parse_qs, urlsplit
import certifi
import pytest

from workspace_db.connection import DatabaseConfigurationError, prepare_database_url


def test_neon_url_requires_full_verification_and_gets_ca_bundle():
    url = 'postgresql://user:secret@example.neon.tech/db?sslmode=verify-full'
    result = prepare_database_url(url, require_verified_tls=True)
    params = parse_qs(urlsplit(result).query)
    assert params['sslmode'] == ['verify-full']
    assert params['sslrootcert'] == [certifi.where()]
    assert urlsplit(result).password == 'secret'


@pytest.mark.parametrize('query', ['', 'sslmode=require', 'sslmode=disable',
    'sslmode=verify-full&channel_binding=require', 'sslmode=verify-full&sslrootcert=system',
    'sslmode=verify-full&sslmode=disable'])
def test_remote_tls_configuration_fails_closed_without_exposing_secret(query):
    with pytest.raises(DatabaseConfigurationError) as exc:
        prepare_database_url('postgresql://user:secret@example.neon.tech/db?' + query, require_verified_tls=True)
    assert 'secret' not in str(exc.value)


def test_local_database_url_is_unchanged():
    local = 'postgresql://gtmuser:gtmpassword@127.0.0.1:5432/gtmops'
    assert prepare_database_url(local) == local


def test_asyncpg_loads_the_ca_bundle_and_enforces_hostname():
    import ssl
    from asyncpg.connect_utils import _parse_connect_dsn_and_args
    url = prepare_database_url('postgresql://user:secret@example.neon.tech/db?sslmode=verify-full', require_verified_tls=True)
    _, params = _parse_connect_dsn_and_args(dsn=url, host=None, port=None, user=None,
        password=None, passfile=None, database=None, ssl=None, service=None,
        servicefile=None, direct_tls=None, server_settings=None,
        target_session_attrs=None, krbsrvname=None, gsslib=None)
    assert params.ssl.check_hostname
    assert params.ssl.verify_mode == ssl.CERT_REQUIRED
