import pytest
from workspace_db.bootstrap_hosted import validate_hosted_config


def test_hosted_bootstrap_requires_verified_tls_and_https_identity():
    validate_hosted_config('postgresql://example.test/db?sslmode=verify-full', 'https://id.example/realms/gtm')
    for url in ('postgresql://example.test/db', 'postgresql://example.test/db?sslmode=require',
                'postgresql://127.0.0.1/db?sslmode=verify-full'):
        with pytest.raises(ValueError):
            validate_hosted_config(url, 'https://id.example/realms/gtm')
    with pytest.raises(ValueError):
        validate_hosted_config('postgresql://example.test/db?sslmode=verify-full', 'http://id.example/realms/gtm')
