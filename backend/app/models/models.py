from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base

class RoleEnum(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"

class SchoolClass(Base):
    __tablename__ = "school_classes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Например: "10 А"
    
    users = relationship("User", back_populates="school_class")
    lessons = relationship("Lesson", back_populates="school_class")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True) # Иванов Иван Иванович
    role = Column(Enum(RoleEnum), default=RoleEnum.student)
    hashed_pin = Column(String) # Хэшированный 4-значный пинкод
    
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=True) # null для учителя
    created_at = Column(DateTime, default=datetime.utcnow)
    
    school_class = relationship("SchoolClass", back_populates="users")
    submissions = relationship("Submission", back_populates="student")

class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"))
    date = Column(Date, index=True) # Дата дедлайна (Вторник или Четверг)
    title = Column(String, nullable=True) # Можно добавить тему урока (опционально)
    
    school_class = relationship("SchoolClass", back_populates="lessons")
    submissions = relationship("Submission", back_populates="lesson")

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    
    submitted_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_on_time = Column(Boolean, default=True) # Сдал вовремя или нет
    text_comment = Column(Text, nullable=True) # Комментарий от ученика (опционально)
    teacher_feedback = Column(Text, nullable=True) # Текстовый фидбек от учителя
    
    student = relationship("User", back_populates="submissions")
    lesson = relationship("Lesson", back_populates="submissions")
    files = relationship("File", back_populates="submission")

class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))
    
    original_name = Column(String) # Например: "domashka.docx"
    file_type = Column(String) # "image/webp", "application/pdf", "application/msword"
    saved_path = Column(String) # Путь на сервере к загруженному файлу
    checked_path = Column(String, nullable=True) # Путь к файлу после проверки учителем (для картинок с canvas)
    
    submission = relationship("Submission", back_populates="files")
