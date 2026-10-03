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
