import sys
import os
from os.path import abspath, dirname
from datetime import date, timedelta, datetime
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.insert(0, dirname(abspath(__file__)))
# Загружаем переменные из .env в корне проекта
load_dotenv(os.path.join(dirname(dirname(abspath(__file__))), '.env'))
load_dotenv()

from app.db.database import SessionLocal, engine, Base
from app.models.models import SchoolClass, Lesson, User, RoleEnum
from app.core.security import get_password_hash

TARGET_CLASSES = ["10 Б", "11 Б", "10 Л", "11 Х"]
TEACHER_USER = os.getenv("TEACHER_USERNAME", "teacher")
TEACHER_PASS = os.getenv("TEACHER_PASSWORD", "SuperSecretPassword2026!")

def setup_database():
    # Создаем таблицы, если их нет (для чистой установки в Docker)
    Base.metadata.create_all(bind=engine)

    # Накатываем недостающие колонки в SQLite
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME;"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE submissions ADD COLUMN updated_at DATETIME;"))
        except Exception:
            pass
        conn.commit()

    db = SessionLocal()

    # 1. Удаляем ненужные старые классы (например, 10 А, 11 А)
    old_classes = db.query(SchoolClass).filter(~SchoolClass.name.in_(TARGET_CLASSES)).all()
    for oc in old_classes:
        # Удаляем привязанные уроки старого класса
        db.query(Lesson).filter(Lesson.class_id == oc.id).delete()
        db.delete(oc)
    db.commit()

    # 2. Создаем нужные классы и уроки на осень 2026
    start_date = date(2026, 9, 1)
    end_date = date(2026, 12, 31)

    for class_name in TARGET_CLASSES:
        sc = db.query(SchoolClass).filter(SchoolClass.name == class_name).first()
        if not sc:
            sc = SchoolClass(name=class_name)
            db.add(sc)
            db.commit()
            db.refresh(sc)

        # Генерируем ВТ и ЧТ
        cur = start_date
        while cur <= end_date:
            if cur.weekday() in (1, 3):
                exists = db.query(Lesson).filter(Lesson.class_id == sc.id, Lesson.date == cur).first()
                if not exists:
                    db.add(Lesson(class_id=sc.id, title="Английский язык", date=cur))
            cur += timedelta(days=1)
        db.commit()

    # 3. Создаем/обновляем учителя из .env
    teacher = db.query(User).filter(User.role == RoleEnum.teacher).first()
    if not teacher:
        teacher = User(
            full_name=TEACHER_USER,
            role=RoleEnum.teacher,
            hashed_pin=get_password_hash(TEACHER_PASS),
            class_id=None
        )
        db.add(teacher)
    else:
        teacher.full_name = TEACHER_USER
        teacher.hashed_pin = get_password_hash(TEACHER_PASS)
        teacher.class_id = None
    db.commit()

    print(f"✅ База готова: классы {TARGET_CLASSES} настроены!")
    print(f"👉 Учитель: {TEACHER_USER} (пароль взят из .env)")
    db.close()

if __name__ == "__main__":
    setup_database()
