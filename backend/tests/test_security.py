"""Tests for security headers middleware."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_security_headers_present():
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age" in r.headers.get("Strict-Transport-Security", "")
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_permissions_policy():
    r = client.get("/health")
    pp = r.headers.get("Permissions-Policy", "")
    assert "camera=()" in pp
    assert "microphone=()" in pp
    assert "geolocation=()" in pp
