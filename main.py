from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
from dotenv import load_dotenv
import motor.motor_asyncio
import io
import os
from bson import ObjectId

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Event Management API")

# Connect to MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not found. Make sure you created a .env file in the project root.")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.event_management  

# Helpers
def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

def stringify_id(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


# Data Models
class Event(BaseModel):
    name: str
    description: str
    date: str
    venue_id: str
    max_attendees: int

class Attendee(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None

class Venue(BaseModel):
    name: str
    address: str
    capacity: int

class Booking(BaseModel):
    event_id: str
    attendee_id: str
    ticket_type: Literal["standard", "vip", "student"]
    quantity: int


# Root 
@app.get("/")
async def root():
    return {"message": "API is running"}


# API Endpoints

# -- Events
@app.post("/events")
async def create_event(event: Event):
    event_doc = event.dict()
    event_doc["created_at"] = datetime.utcnow()
    result = await db.events.insert_one(event_doc)
    return {"message": "Event created", "id": str(result.inserted_id)}

@app.get("/events")
async def get_events():
    events = await db.events.find().to_list(100)
    return [stringify_id(e) for e in events]

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    doc = await db.events.find_one({"_id": to_object_id(event_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return stringify_id(doc)


# -- Attendees
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    attendee_doc = attendee.dict()
    attendee_doc["created_at"] = datetime.utcnow()
    result = await db.attendees.insert_one(attendee_doc)
    return {"message": "Attendee created", "id": str(result.inserted_id)}

@app.get("/attendees")
async def get_attendees():
    attendees = await db.attendees.find().to_list(100)
    return [stringify_id(a) for a in attendees]

@app.get("/attendees/{attendee_id}")
async def get_attendee(attendee_id: str):
    doc = await db.attendees.find_one({"_id": to_object_id(attendee_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return stringify_id(doc)


# -- Venues
@app.post("/venues")
async def create_venue(venue: Venue):
    venue_doc = venue.dict()
    venue_doc["created_at"] = datetime.utcnow()
    result = await db.venues.insert_one(venue_doc)
    return {"message": "Venue created", "id": str(result.inserted_id)}

@app.get("/venues")
async def get_venues():
    venues = await db.venues.find().to_list(100)
    return [stringify_id(v) for v in venues]

@app.get("/venues/{venue_id}")
async def get_venue(venue_id: str):
    doc = await db.venues.find_one({"_id": to_object_id(venue_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Venue not found")
    return stringify_id(doc)


# -- Bookings
@app.post("/bookings")
async def create_booking(booking: Booking):
    booking_doc = booking.dict()
    booking_doc["created_at"] = datetime.utcnow()
    result = await db.bookings.insert_one(booking_doc)
    return {"message": "Booking created", "id": str(result.inserted_id)}

@app.get("/bookings")
async def get_bookings():
    bookings = await db.bookings.find().to_list(100)
    return [stringify_id(b) for b in bookings]

@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    doc = await db.bookings.find_one({"_id": to_object_id(booking_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return stringify_id(doc)


# -- Media Upload + Retrieve
@app.post("/upload_event_poster/{event_id}")
async def upload_event_poster(event_id: str, file: UploadFile = File(...)):
    content = await file.read()

    doc = {
        "type": "event_poster",
        "related_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    result = await db.multimedia.insert_one(doc)
    return {"message": "File uploaded", "id": str(result.inserted_id)}


@app.post("/upload_promo_video/{event_id}")
async def upload_promo_video(event_id: str, file: UploadFile = File(...)):
    content = await file.read()

    doc = {
        "type": "promo_video",
        "related_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    result = await db.multimedia.insert_one(doc)
    return {"message": "File uploaded", "id": str(result.inserted_id)}


@app.post("/upload_venue_photo/{venue_id}")
async def upload_venue_photo(venue_id: str, file: UploadFile = File(...)):
    content = await file.read()

    doc = {
        "type": "venue_photo",
        "related_id": venue_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    result = await db.multimedia.insert_one(doc)
    return {"message": "File uploaded", "id": str(result.inserted_id)}


@app.get("/media/{media_id}")
async def get_media(media_id: str):
    doc = await db.multimedia.find_one({"_id": to_object_id(media_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    return StreamingResponse(
        io.BytesIO(doc["content"]),
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'inline; filename="{doc["filename"]}"'}
    )
