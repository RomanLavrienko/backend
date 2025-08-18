from infrastructure.repositiry.verification_repository import VerificationRepository
import secrets
import logging
from datetime import datetime, timedelta

phone_codes = {}

class VerificationService:
    def __init__(self,session):
        self.session = session
        self.verification_repository = VerificationRepository(session)

    def _verify_by_phone(self, user_id):
        self.verification_repository.verify_by_phone(user_id)

    def _verify_by_admin(self, user_id):
        self.verification_repository.verify_by_admin(user_id)

    async def send_phone_code(self, phone: str):
        code = secrets.randbelow(10000)
        code = str(code).zfill(4)
        phone_codes[phone] = (code, datetime.utcnow() + timedelta(minutes=5))
        logging.error(f"Код подтверждения для {phone}: {code}")
        return True

    async def verify_phone_code(self, phone: str, code: str) -> bool:
        if phone not in phone_codes:
            return False

        stored_code, expiration = phone_codes[phone]
        if datetime.utcnow() > expiration:
            return False

        return stored_code == code