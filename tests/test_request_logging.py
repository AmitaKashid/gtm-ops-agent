import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.logging import RequestLoggingMiddleware


def test_request_log_has_status_and_omits_query(caplog):
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get('/example')
    def example():
        return {'ok': True}

    with caplog.at_level(logging.INFO, logger='api.middleware.logging'):
        response = TestClient(app).get('/example?secret=example')

    assert response.status_code == 200
    assert len(response.headers['X-Request-ID']) == 8
    assert 'status=200' in caplog.text
    assert 'secret=example' not in caplog.text
