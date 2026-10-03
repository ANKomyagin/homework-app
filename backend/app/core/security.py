from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

# Секретный ключ для подписи токена (в будущем вынесем в .env)
SECRET_KEY = "super-secret-key-for-homework-app"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30 # Токен будет жить 30 дней (чтобы не логиниться часто)

# Настройка passlib для хэширования ПИН-кодов
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    return pwd_context.verify(plain_pin, hashed_pin)

def get_password_hash(pin: str) -> str:
    return pwd_context.hash(pin)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
