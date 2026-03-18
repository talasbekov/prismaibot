import hmac
import hashlib
import pytest
from app.billing.utils import verify_apipay_signature, normalize_phone_number

def test_normalize_phone_number():
    assert normalize_phone_number("+7 (701) 123-45-67") == "87011234567"
    assert normalize_phone_number("87011234567") == "87011234567"
    assert normalize_phone_number("7011234567") == "87011234567"
    assert normalize_phone_number("8-701-1234567") == "87011234567"

def test_verify_apipay_signature_success():
    secret = "test_secret"
    payload = b'{"event": "test"}'
    signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    
    assert verify_apipay_signature(payload, signature, secret) is True

def test_verify_apipay_signature_failure():
    secret = "test_secret"
    payload = b'{"event": "test"}'
    signature = "sha256=wrong_hash"
    
    assert verify_apipay_signature(payload, signature, secret) is False

def test_verify_apipay_signature_invalid_format():
    secret = "test_secret"
    payload = b'{"event": "test"}'
    signature = "md5=wrong_format"
    
    assert verify_apipay_signature(payload, signature, secret) is False

def test_verify_apipay_signature_no_secret():
    payload = b'{"event": "test"}'
    signature = "sha256=some_hash"
    
    # settings.APIPAY_WEBHOOK_SECRET is None by default in tests
    assert verify_apipay_signature(payload, signature, None) is False
