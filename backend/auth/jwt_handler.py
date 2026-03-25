from datetime import datetime, timedelta, timezone
import os
from jose import JWTError, jwt


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    # Docker --env-file y algunos .env incluyen comentario inline: "1440 # minutos"
    raw = raw.split("#", 1)[0].strip()
    try:
        return int(raw)
    except ValueError:
        return default


# Secret key recomendada traida del .env
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None