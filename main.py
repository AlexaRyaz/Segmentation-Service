from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel
import sqlite3
import database  # Импортируем модуль с функциями БД


# Модели данных для API
class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None


class SegmentCreate(BaseModel):
    segment: str
    description: Optional[str] = None


class SegmentDistribution(BaseModel):
    percent: int


class MoveUsersRequest(BaseModel):
    from_segment: str
    to_segment: str


# Обработчик жизненного цикла сервиса
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД при старте
    database.init_db()
    yield
    print("Server shutting down")


# Создаем FastAPI
app = FastAPI(lifespan=lifespan)


# Зависимость для получения соединения с БД
def get_db():
    with database.get_db_connection() as conn:
        yield conn


# Корневой endpoint
@app.get("/")
def read_root():
    return {"message": "Segment Management API is running"}


# Создание нового пользователя
@app.post("/users/", status_code=201)
def create_user(user: UserCreate):
    try:
        database.add_user(user.name, user.email)
        return {"message": "User created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already exists")


# Получить список всех пользователей
@app.get("/users/", response_model=List[dict])
def get_all_users():
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email FROM Users")
        return [dict(row) for row in cursor.fetchall()]


# Получить сегменты пользователя
@app.get("/users/{user_id}/segments", response_model=List[str])
def get_user_segments(user_id: int):
    segments = database.get_user_segments(user_id)
    if not segments:
        raise HTTPException(status_code=404, detail="User not found or has no segments")
    return segments


# Создать новый сегмент
@app.post("/segments/", status_code=201)
def create_segment(segment: SegmentCreate):
    try:
        database.add_segment(segment.segment, segment.description)
        return {"message": "Segment created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Segment already exists")


# Получить список всех сегментов
@app.get("/segments/", response_model=List[dict])
def get_all_segments():
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT segment, description FROM Segments")
        return [dict(row) for row in cursor.fetchall()]


# Удалить сегмент
@app.delete("/segments/{segment_name}")
def delete_segment(segment_name: str):
    try:
        database.delete_segment(segment_name)
        return {"message": "Segment deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Обновить описание сегмента
@app.put("/segments/{segment_name}/description")
def update_segment_description(segment_name: str, new_description: str):
    try:
        database.update_segment_description(segment_name, new_description)
        return {"message": "Description updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Добавить пользователя в сегмент
@app.post("/users/{user_id}/segments/{segment_name}")
def add_user_to_segment(user_id: int, segment_name: str):
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Segments WHERE segment = ?", (segment_name,))
            segment = cursor.fetchone()
            if not segment:
                raise HTTPException(status_code=404, detail="Segment not found")

            database.add_user_to_segment(user_id, segment['id'])
            return {"message": "User added to segment successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Удалить пользователя из сегмента
@app.delete("/users/{user_id}/segments/{segment_name}")
def remove_user_from_segment(user_id: int, segment_name: str):
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            # Получаем ID сегмента
            cursor.execute("SELECT id FROM Segments WHERE segment = ?", (segment_name,))
            segment = cursor.fetchone()
            if not segment:
                raise HTTPException(status_code=404, detail="Segment not found")

            database.delete_user_in_segment(user_id, segment['id'])
            return {"message": "User removed from segment successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Распределить сегмент на процент пользователей
@app.post("/segments/{segment_name}/distribute")
def distribute_segment(segment_name: str, distribution: SegmentDistribution):
    try:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM Segments WHERE segment = ?", (segment_name,))
            segment = cursor.fetchone()
            if not segment:
                raise HTTPException(status_code=404, detail="Segment not found")

            database.distribute_segment_to_percent(segment['id'], distribution.percent)
            return {"message": f"Segment distributed to {distribution.percent}% of users"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Перенести пользователей между сегментами
@app.post("/segments/move_users")
def move_users(request: MoveUsersRequest):
    try:
        database.move_users_between_segments(request.from_segment, request.to_segment)
        return {"message": f"Users moved from {request.from_segment} to {request.to_segment}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Получить статистику по сегментам
@app.get("/segments/stats")
def get_segments_stats():
    return database.get_segments_stats()


# Получить пользователей в сегменте
@app.get("/segments/{segment_name}/users")
def get_segment_users(segment_name: str):
    users = database.get_users_in_segment(segment_name)
    if not users:
        raise HTTPException(status_code=404, detail="Segment not found or has no users")
    return {"users": users}


# Получить информацию о сегменте
@app.get("/segments/{segment_name}", response_model=dict)
def get_segment_info(segment_name: str):
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT segment, description FROM Segments WHERE segment = ?",
            (segment_name,)
        )
        segment = cursor.fetchone()
        if not segment:
            raise HTTPException(status_code=404, detail="Segment not found")
        return dict(segment)


# Проверить, состоит ли пользователь в сегменте
@app.get("/users/{user_id}/segments/{segment_name}", response_model=dict)
def check_user_in_segment(user_id: int, segment_name: str):
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        # Получаем ID сегмента
        cursor.execute("SELECT id FROM Segments WHERE segment = ?", (segment_name,))
        segment = cursor.fetchone()
        if not segment:
            raise HTTPException(status_code=404, detail="Segment not found")

        # Проверяем связь
        cursor.execute(
            "SELECT 1 FROM U_S WHERE user_id = ? AND segment_id = ?",
            (user_id, segment['id'])
        )
        exists = cursor.fetchone() is not None
        return {
            "user_id": user_id,
            "segment": segment_name,
            "is_member": exists
        }


# Получить информацию о распределении сегмента
@app.get("/segments/{segment_name}/distribute", response_model=dict)
def get_distribution_info(segment_name: str):
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM Segments WHERE segment = ?", (segment_name,))
        segment = cursor.fetchone()
        if not segment:
            raise HTTPException(status_code=404, detail="Segment not found")

        # Получаем количество пользователей в сегменте
        cursor.execute(
            "SELECT COUNT(*) FROM U_S WHERE segment_id = ?",
            (segment['id'],)
        )
        count = cursor.fetchone()[0]

        # Получаем общее количество пользователей
        cursor.execute("SELECT COUNT(*) FROM Users")
        total = cursor.fetchone()[0]

        percent = (count / total) * 100 if total > 0 else 0

        return {
            "segment": segment_name,
            "user_count": count,
            "total_users": total,
            "percent": round(percent, 2)
        }