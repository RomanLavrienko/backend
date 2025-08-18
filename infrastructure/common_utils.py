from fastapi import Cookie, HTTPException
import logging
import jwt

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"


async def get_current_user(access_token: str = Cookie(None)) -> dict:
    if not access_token:
        return None

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        logging.exception("Token decoding error")
        raise HTTPException(500, "Token processing error")