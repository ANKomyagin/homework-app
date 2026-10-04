import time
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, RoleEnum, SchoolClass
from app.schemas.user import UserCreate, UserLogin, UserResponse, TeacherLogin
from app.core.security import get_password_hash, verify_pin, create_access_token

router = APIRouter(prefix="/auth", tags=["Авторизация"])

# === СЛОВАРИ ДЛЯ ЗАЩИТЫ ОТ БРУТФОРСА В ПАМЯТИ ===
student_attempts = {} # ip -> timestamp последнего входа
teacher_attempts = {} # ip -> {"count": int, "blocked_until": float}

def get_client_ip(request: Request) -> str:
    """Извлекаем реальный IP пользователя из-под Nginx"""
    if forwarded := request.headers.get("X-Forwarded-For"):
        return forwarded.split(",")[0].strip()
    if real_ip := request.headers.get("X-Real-IP"):
        return real_ip.strip()
    return request.client.host

def check_student_rate_limit(request: Request):
    """Статичный кулдаун 3 секунды для учеников"""
    ip = get_client_ip(request)
    now = time.time()
    last_attempt = student_attempts.get(ip, 0)
    if now - last_attempt < 3:
        raise HTTPException(status_code=429, detail="Слишком частые попытки. Подождите 3 секунды.")
    student_attempts[ip] = now


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    check_student_rate_limit(request)
    
    school_class = db.query(SchoolClass).filter(SchoolClass.id == user_data.class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Класс не найден")

    formatted_name = user_data.full_name.strip().title()
    existing_user = db.query(User).filter(
        User.full_name == formatted_name,
        User.class_id == user_data.class_id
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Ученик с таким именем уже есть в классе")

    new_user = User(
        full_name=formatted_name,
        class_id=user_data.class_id,
        role=RoleEnum.student,
        hashed_pin=get_password_hash(user_data.pin)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login")
def login(user_data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    check_student_rate_limit(request)
    
    formatted_name = user_data.full_name.strip().title()
    user = db.query(User).filter(
        User.full_name == formatted_name,
        User.class_id == user_data.class_id
    ).first()
    
    if not user or not verify_pin(user_data.pin, user.hashed_pin):
        raise HTTPException(status_code=401, detail="Неверное имя, класс или пароль")

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        max_age=30 * 24 * 60 * 60,
        samesite="lax"
    )
    return {"message": "Успешный вход", "user": {"id": user.id, "full_name": user.full_name}}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Успешный выход"}


@router.post("/teacher/login")
def teacher_login(data: TeacherLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    now = time.time()
    
    # 1. Проверяем, не заблокирован ли IP учителя
    record = teacher_attempts.get(ip, {"count": 0, "blocked_until": 0})
    if now < record["blocked_until"]:
        wait_time = int(record["blocked_until"] - now)
        raise HTTPException(status_code=429, detail=f"Слишком много ошибок. Подождите {wait_time} сек.")

    # 2. Ищем пользователя
    user = db.query(User).filter(
        User.full_name == data.username.strip(),
        User.role == RoleEnum.teacher
    ).first()
    
    if not user or not verify_pin(data.password, user.hashed_pin):
        # 3. Увеличиваем счетчик ошибок и наказываем кулдауном
        record["count"] += 1
        # Логика: 1 ошибка -> 3 сек, 2 ошибки -> 5 сек, 3 ошибки -> 7 сек...
        penalty = 3 + (record["count"] - 1) * 2
        record["blocked_until"] = time.time() + penalty
        teacher_attempts[ip] = record
        
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    # 4. Если пароль верный, обнуляем ошибки для этого IP
    if ip in teacher_attempts:
        del teacher_attempts[ip]

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        max_age=30 * 24 * 60 * 60,
        samesite="lax"
    )
    return {"message": "Успешный вход учителя", "user": {"id": user.id, "role": user.role.value}}
