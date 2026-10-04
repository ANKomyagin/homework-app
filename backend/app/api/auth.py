from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, RoleEnum, SchoolClass
from app.schemas.user import UserCreate, UserLogin, UserResponse, TeacherLogin
from app.core.security import get_password_hash, verify_pin, create_access_token

router = APIRouter(prefix="/auth", tags=["Авторизация"])

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Проверяем, существует ли класс
    school_class = db.query(SchoolClass).filter(SchoolClass.id == user_data.class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="Класс не найден")

    # Нормализуем имя силами Python: убираем пробелы и делаем с большой буквы (Иванов Иван)
    formatted_name = user_data.full_name.strip().title()

    existing_user = db.query(User).filter(
        User.full_name == formatted_name,
        User.class_id == user_data.class_id
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Ученик с таким именем уже есть в классе")

    # Сохраняем имя в красивом виде с заглавной буквы (Иванов Иван)
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
def login(user_data: UserLogin, response: Response, db: Session = Depends(get_db)):
    # Точно так же нормализуем имя при входе
    formatted_name = user_data.full_name.strip().title()
    
    user = db.query(User).filter(
        User.full_name == formatted_name,
        User.class_id == user_data.class_id
    ).first()
    
    if not user or not verify_pin(user_data.pin, user.hashed_pin):
        raise HTTPException(status_code=401, detail="Неверное имя, класс или ПИН-код")

    # Создаем JWT токен
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    
    # Кладём токен в куки браузера
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # Защита от XSS (JS во фронтенде не сможет украсть куки)
        secure=True,
        max_age=30 * 24 * 60 * 60, # 30 дней в секундах
        samesite="lax"
    )
    return {"message": "Успешный вход", "user": {"id": user.id, "full_name": user.full_name}}

@router.post("/logout")
def logout(response: Response):
    # Удаляем куки при выходе
    response.delete_cookie("access_token")
    return {"message": "Успешный выход"}

@router.post("/teacher/login")
def teacher_login(data: TeacherLogin, response: Response, db: Session = Depends(get_db)):
    # Ищем пользователя с ролью teacher по логину
    user = db.query(User).filter(
        User.full_name == data.username.strip(),
        User.role == RoleEnum.teacher
    ).first()
    
    if not user or not verify_pin(data.password, user.hashed_pin):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль учителя")

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
