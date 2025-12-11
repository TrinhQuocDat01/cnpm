#.\venv\Scripts\activate: kich hoat venv
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# =========================
#  Cấu hình DB SQLite
# =========================
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    room_name = Column(String, index=True)
    date = Column(Date, index=True)
    start_time = Column(String)
    end_time = Column(String)
    purpose = Column(String)


Base.metadata.create_all(bind=engine)

class BookingCreate(BaseModel):
    room_name: str
    date: str
    start_time: str
    end_time: str
    purpose: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()

# CORS (dự phòng nếu chạy frontend ở port khác)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/bookings")
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    try:
        booking_date = datetime.strptime(booking.date, "%Y-%m-%d").date()
    except:
        raise HTTPException(status_code=400, detail="Ngày không đúng định dạng.")

    existing = (
        db.query(Booking)
        .filter(Booking.room_name == booking.room_name)
        .filter(Booking.date == booking_date)
        .all()
    )

    for b in existing:
        if not (booking.end_time <= b.start_time or booking.start_time >= b.end_time):
            raise HTTPException(
                status_code=400,
                detail="Khung giờ này đã có người đặt rồi!"
            )

    new_booking = Booking(
        room_name=booking.room_name,
        date=booking_date,
        start_time=booking.start_time,
        end_time=booking.end_time,
        purpose=booking.purpose,
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return {
        "id": new_booking.id,
        "room_name": new_booking.room_name,
        "date": str(new_booking.date),
        "start_time": new_booking.start_time,
        "end_time": new_booking.end_time,
        "purpose": new_booking.purpose,
    }

@app.get("/api/bookings")
def get_bookings(date: str, db: Session = Depends(get_db)):
    """Lấy tất cả lịch đặt phòng theo ngày"""
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
    except:
        raise HTTPException(status_code=400, detail="Sai định dạng ngày")

    bookings = db.query(Booking).filter(Booking.date == booking_date).all()
    return [
        {
            "id": b.id,
            "room_name": b.room_name,
            "start_time": b.start_time,
            "end_time": b.end_time,
            "purpose": b.purpose,
        }
        for b in bookings
    ]

@app.delete("/api/bookings/{booking_id}")
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy đặt phòng")

    db.delete(booking)
    db.commit()
    return {"message": "Đã xóa đặt phòng"}
