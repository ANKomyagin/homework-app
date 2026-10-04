from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import SchoolClass, Lesson, User, Submission, File as DBFile, RoleEnum
from app.api.deps import get_current_user

router = APIRouter(tags=["Дашборды"])

@router.get("/classes")
def get_classes(db: Session = Depends(get_db)):
    return db.query(SchoolClass).all()

@router.get("/student/lessons")
def get_student_lessons(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != RoleEnum.student:
        raise HTTPException(status_code=403, detail="Только для учеников")
    
    lessons = db.query(Lesson).filter(Lesson.class_id == current_user.class_id).order_by(Lesson.date).all()
    submissions = db.query(Submission).filter(Submission.student_id == current_user.id).all()
    sub_map = {s.lesson_id: s for s in submissions}
    
    # Собираем файлы сдачи
    sub_ids = [s.id for s in submissions]
    files = db.query(DBFile).filter(DBFile.submission_id.in_(sub_ids)).all()
    files_by_sub = {}
    for f in files:
        if f.submission_id not in files_by_sub:
            files_by_sub[f.submission_id] = []
        normalized_path = f.saved_path.replace('\\', '/')
        files_by_sub[f.submission_id].append({
            "id": f.id,
            "name": f.original_name,
            "url": f"/{normalized_path}"
        })

    result = []
    for l in lessons:
        sub = sub_map.get(l.id)
        result.append({
            "id": l.id,
            "date": l.date.isoformat(),
            "title": l.title,
            "submission": {
                "id": sub.id,
                "is_on_time": sub.is_on_time,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
                "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
                "comment": sub.text_comment,
                "teacher_feedback": sub.teacher_feedback,
                "files": files_by_sub.get(sub.id, [])
            } if sub else None
        })

    return {
        "user_created_at": current_user.created_at.isoformat() if current_user.created_at else "2026-09-01T00:00:00",
        "lessons": result
    }

@router.get("/teacher/dashboard/{class_id}")
def get_teacher_dashboard(class_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in [RoleEnum.teacher, RoleEnum.admin]:
        raise HTTPException(status_code=403, detail="Только для учителя")
        
    lessons = db.query(Lesson).filter(Lesson.class_id == class_id).order_by(Lesson.date).all()
    students = db.query(User).filter(User.class_id == class_id, User.role == RoleEnum.student).all()
    
    lesson_ids = [l.id for l in lessons]
    submissions = db.query(Submission).filter(Submission.lesson_id.in_(lesson_ids)).all()
    
    # Собираем и группируем файлы по сдаче
    sub_ids = [s.id for s in submissions]
    files = db.query(DBFile).filter(DBFile.submission_id.in_(sub_ids)).all()
    files_by_sub = {}
    for f in files:
        if f.submission_id not in files_by_sub:
            files_by_sub[f.submission_id] = []
        normalized_path = f.saved_path.replace('\\', '/')
        files_by_sub[f.submission_id].append({
            "id": f.id,
            "name": f.original_name,
            "type": f.file_type,
            # Формируем публичную ссылку на файл
            "url": f"/{normalized_path}"
        })
    
    subs_dict = {}
    for s in submissions:
        key = f"{s.student_id}_{s.lesson_id}"
        subs_dict[key] = {
            "id": s.id,
            "is_on_time": s.is_on_time,
            "comment": s.text_comment,
            "feedback": s.teacher_feedback,
            "files": files_by_sub.get(s.id, [])
        }
        
    return {
        "lessons": [{"id": l.id, "title": l.title, "date": l.date} for l in lessons],
        "students": [{"id": st.id, "name": st.full_name} for st in students],
        "submissions": subs_dict
    }

@router.post("/teacher/feedback/{submission_id}")
def save_feedback(
    submission_id: int, 
    feedback: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role not in [RoleEnum.teacher, RoleEnum.admin]:
        raise HTTPException(status_code=403, detail="Только для учителя")
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Сдача не найдена")
    sub.teacher_feedback = feedback
    db.commit()
    return {"message": "Отзыв успешно сохранен"}
