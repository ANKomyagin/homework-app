from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api import auth, submissions, dashboard # Добавляем импорт
from app.db.database import get_db
from app.models.models import SchoolClass, Lesson
from datetime import date

app = FastAPI(
    title="Homework App API",
    description="API для загрузки домашних заданий",
    version="1.0.0"
)

# Настройка CORS, чтобы фронтенд (Svelte) мог без проблем обращаться к бэкенду
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # В продакшене заменим на домен сайта
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутер авторизации
app.include_router(auth.router)
app.include_router(submissions.router)
app.include_router(dashboard.router)
app.mount("/media", StaticFiles(directory="media"), name="media")

@app.get("/")
def read_root():
    return {"message": "Сервер успешно запущен! База данных готова."}

@app.post("/create_class_test")
def create_class(name: str, db: Session = Depends(get_db)):
    new_class = SchoolClass(name=name)
    db.add(new_class)
    db.commit()
    return new_class

@app.post("/create_lesson_test")
def create_lesson(class_id: int, title: str, deadline: date, db: Session = Depends(get_db)):
    new_lesson = Lesson(class_id=class_id, title=title, date=deadline)
    db.add(new_lesson)
    db.commit()
    return new_lesson

import os
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.db.database import engine
from app.core.security import SECRET_KEY
from app.models.models import User, SchoolClass, Lesson, Submission, File as DBFile

# 1. ЗАЩИТА АДМИНКИ (Авторизация)
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form.get("username"), form.get("password")
        
        env_user = os.getenv("TEACHER_USERNAME", "teacher")
        env_pass = os.getenv("TEACHER_PASSWORD", "SuperSecretPassword2026!")
        
        if username == env_user and password == env_pass:
            request.session.update({"token": "admin_logged_in"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        return token == "admin_logged_in"

authentication_backend = AdminAuth(secret_key=SECRET_KEY)

# 2. ИНИЦИАЛИЗАЦИЯ SQLADMIN
admin = Admin(app, engine, authentication_backend=authentication_backend)

# 3. НАСТРОЙКА ОТОБРАЖЕНИЯ ТАБЛИЦ
class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"
    column_list = [User.id, User.full_name, User.role, User.class_id, User.created_at]
    column_searchable_list = [User.full_name]
    column_sortable_list = [User.id, User.full_name, User.created_at]

class ClassAdmin(ModelView, model=SchoolClass):
    name = "Класс"
    name_plural = "Классы"
    icon = "fa-solid fa-school"
    column_list = [SchoolClass.id, SchoolClass.name]

class LessonAdmin(ModelView, model=Lesson):
    name = "Урок"
    name_plural = "Уроки"
    icon = "fa-solid fa-book"
    column_list = [Lesson.id, Lesson.date, Lesson.title, Lesson.class_id]

class SubmissionAdmin(ModelView, model=Submission):
    name = "Сдача ДЗ"
    name_plural = "Сдачи ДЗ"
    icon = "fa-solid fa-file-upload"
    column_list = [Submission.id, Submission.student_id, Submission.lesson_id, Submission.is_on_time, Submission.submitted_at]

class FileAdmin(ModelView, model=DBFile):
    name = "Файл"
    name_plural = "Файлы"
    icon = "fa-solid fa-file"
    column_list = [DBFile.id, DBFile.original_name, DBFile.file_type, DBFile.submission_id]

# 4. РЕГИСТРИРУЕМ ВЬЮХИ
admin.add_view(UserAdmin)
admin.add_view(ClassAdmin)
admin.add_view(LessonAdmin)
admin.add_view(SubmissionAdmin)
admin.add_view(FileAdmin)
