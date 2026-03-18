import hmac
import hashlib
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def verify_apipay_signature(payload: bytes, signature: str | None, secret: str | None = None) -> bool:
    """
    Verify the HMAC SHA256 signature from ApiPay.kz.
    
    The signature is expected in the format 'sha256=<hash>'.
    """
    webhook_secret = secret or settings.APIPAY_WEBHOOK_SECRET
    if not webhook_secret:
        logger.error("APIPAY_WEBHOOK_SECRET is not configured!")
        return False
        
    if not signature or not isinstance(signature, str) or not signature.startswith("sha256="):
        return False
        
    parts = signature.split("=")
    if len(parts) != 2:
        return False
        
    actual_hash = parts[1]
    expected_hash = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_hash, actual_hash)

def normalize_phone_number(phone: str | None) -> str:
    """
    Normalize phone number to '8XXXXXXXXXX' format required by Kaspi if applicable, 
    otherwise return digits only.
    """
    if not phone:
        return ""
        
    # Remove all non-digit characters
    digits = "".join(filter(str.isdigit, str(phone)))
    
    # Handle common cases for Kazakhstan
    if digits.startswith("7") and len(digits) == 11:
        return "8" + digits[1:]
        
    # If 10 digits and starts with 7 (e.g. 701...), assume it's missing the +7/8 prefix
    if len(digits) == 10 and digits.startswith("7"):
        return "8" + digits
    
    # If already local format, keep it
    if digits.startswith("8") and len(digits) == 11:
        return digits
        
    # Fallback for international / other numbers: return as is
    return digits
