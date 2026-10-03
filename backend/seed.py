import sys
from os.path import abspath, dirname
from datetime import date, timedelta, datetime
from sqlalchemy import text

sys.path.insert(0, dirname(abspath(__file__)))

from app.db.database import SessionLocal, engine
from app.models.models import SchoolClass, Lesson, User, RoleEnum
from app.core.security import get_password_hash

def apply_migrations_and_seed():
    # Добавляем новые колонки в SQLite, если их еще нет
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN created_at DATETIME;"))
            print("Добавлена колонка users.created_at")
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE submissions ADD COLUMN updated_at DATETIME;"))
            print("Добавлена колонка submissions.updated_at")
        except Exception:
            pass
        conn.commit()

    db = SessionLocal()

    # 1. Убираем "Русский язык", переименовываем все уроки в Английский язык
    db.query(Lesson).update({Lesson.title: "Английский язык"})
    db.commit()

    # 2. Если у учеников нет даты регистрации, ставим текущую
    db.query(User).filter(User.created_at == None).update({User.created_at: datetime.utcnow()})
    db.commit()

    # 3. Проверяем класс 10 А
    school_class = db.query(SchoolClass).filter(SchoolClass.name == "10 А").first()
    if not school_class:
        school_class = SchoolClass(name="10 А")
        db.add(school_class)
        db.commit()
        db.refresh(school_class)

    # 4. Генерируем ВТ и ЧТ на осень 2026
    start_date = date(2026, 9, 1)
    end_date = date(2026, 12, 31)
    cur = start_date
    while cur <= end_date:
        if cur.weekday() in (1, 3):
            exists = db.query(Lesson).filter(Lesson.class_id == school_class.id, Lesson.date == cur).first()
            if not exists:
                db.add(Lesson(class_id=school_class.id, title="Английский язык", date=cur))
        cur += timedelta(days=1)
    db.commit()

    # 5. Учитель
    teacher = db.query(User).filter(User.role == RoleEnum.teacher).first()
    if not teacher:
        db.add(User(full_name="teacher", role=RoleEnum.teacher, hashed_pin=get_password_hash("admin123"), class_id=None))
    db.commit()

    print("✅ База обновлена: 'Русский язык' удален, колонки дат добавлены!")
    db.close()

if __name__ == "__main__":
    apply_migrations_and_seed()
