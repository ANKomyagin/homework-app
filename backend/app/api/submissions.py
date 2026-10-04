import os
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import Image
from typing import List, Optional

MSK = timezone(timedelta(hours=3))

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User, Lesson, Submission, File as DBFile
from app.api.deps import get_current_user

router = APIRouter(prefix="/submissions", tags=["Домашние задания"])

# Папка, куда будут сохраняться файлы
MEDIA_DIR = Path("media/submissions")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ
MAX_FILES_COUNT = 10

@router.post("/{lesson_id}")
async def upload_submission(
    lesson_id: int,
    text_comment: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Проверки
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Урок не найден")

    if len(files) > MAX_FILES_COUNT:
        raise HTTPException(status_code=400, detail=f"Максимум {MAX_FILES_COUNT} файлов")

    for file in files:
        if file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"Файл {file.filename} превышает 10 МБ")

    # Ищем, сдавал ли уже ученик это ДЗ. Если да - обновим, если нет - создадим.
    submission = db.query(Submission).filter(
        Submission.student_id == current_user.id,
        Submission.lesson_id == lesson_id
    ).first()

    # Проверка на дедлайн: вовремя ли сдано?
    # Если текущая дата меньше или равна дате урока, то вовремя.
    is_on_time = datetime.now(MSK).date() <= lesson.date

    if not submission:
        submission = Submission(
            student_id=current_user.id,
            lesson_id=lesson_id,
            text_comment=text_comment,
            is_on_time=is_on_time,
            updated_at=datetime.now(MSK)
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
    else:
        submission.updated_at = datetime.now(MSK) # <-- Фиксируем дату изменения
        if text_comment is not None:
            submission.text_comment = text_comment
        db.commit()

    # 2. Сохранение файлов
    # Структура папок: media/submissions/class_id/lesson_id/student_id/
    save_dir = MEDIA_DIR / str(current_user.class_id) / str(lesson_id) / str(current_user.id)
    save_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for upload_file in files:
        file_ext = Path(upload_file.filename).suffix.lower()
        base_name = Path(upload_file.filename).stem
        
        # Генерируем уникальное имя файла, чтобы не перезаписать случайные совпадения
        unique_filename = f"{base_name}_{int(datetime.now(MSK).timestamp())}{file_ext}"
        file_path = save_dir / unique_filename

        # Проверяем, картинка ли это
        is_image = upload_file.content_type.startswith('image/')

        if is_image:
            # Конвертируем в WebP
            try:
                image = Image.open(upload_file.file)
                # Переводим в RGB, если есть альфа-канал (чтобы избежать ошибок JPEG/WebP)
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                
                webp_filename = f"{base_name}_{int(datetime.now(MSK).timestamp())}.webp"
                file_path = save_dir / webp_filename
                
                image.save(file_path, "WEBP", quality=80)
                file_type = "image/webp"
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Ошибка обработки изображения {upload_file.filename}")
        else:
            # Сохраняем как есть (pdf, docx, txt)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            file_type = upload_file.content_type

        # Запись информации о файле в БД
        db_file = DBFile(
            submission_id=submission.id,
            original_name=upload_file.filename,
            file_type=file_type,
            saved_path=str(file_path)
        )
        db.add(db_file)
        saved_files.append(db_file)

    db.commit()

    return {
        "message": "Домашнее задание успешно загружено",
        "submission_id": submission.id,
        "files_saved": len(saved_files),
        "is_on_time": submission.is_on_time
    }


@router.delete("/files/{file_id}")
def delete_file(file_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_file = db.query(DBFile).filter(DBFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    submission = db.query(Submission).filter(Submission.id == db_file.submission_id).first()
    if submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа")

    # Удаляем физический файл с диска
    try:
        if os.path.exists(db_file.saved_path):
            os.remove(db_file.saved_path)
    except Exception:
        pass

    db.delete(db_file)
    submission.updated_at = datetime.now(MSK) # Обновляем время изменения сдачи
    db.commit()
    return {"message": "Файл успешно удален"}
