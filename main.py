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
# to_object_id is used to convert a string to a MongoDB ObjectId
# This is needed when the endpoint receives an id as a string parameter
# If the conversion fails, an HTTP 400 error is raised
 
def to_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId format")

# stringify_id converts the ObjectId in a document to a string for JSON responses
# MongoDB returns _id as an ObjectId, which is not JSON serializable
# This function modifies the document in place and returns it
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
# Quick tetst endpoint to verify API is running
@app.get("/")
async def root():
    return {"message": "API is running"}


# API Endpoints

# -- Events
# Post/events; create a new event
# a new event is created with the provided details and stored in the database
# if successful, returns the id of the created event
@app.post("/events")
async def create_event(event: Event):
    event_doc = event.dict()
    event_doc["created_at"] = datetime.utcnow()
    result = await db.events.insert_one(event_doc)
    return {"message": "Event created", "id": str(result.inserted_id)}

# Get/events; retrieve all events
# fetches up to a 100 events from the database and returns them as a list
@app.get("/events")
async def get_events():
    events = await db.events.find().to_list(100)
    return [stringify_id(e) for e in events]

# Get/events/{event_id}; retrieve a specific event by id
# fetches the event with the specified id from the database
# if event is found, returns the event details
# if the event is not found, returns a 404 error
@app.get("/events/{event_id}")
async def get_event(event_id: str):
    doc = await db.events.find_one({"_id": to_object_id(event_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return stringify_id(doc)

# Put/events/{event_id}; update an existing event by id
# updates the event with the specified id using the provided details
@app.put("/events/{event_id}")
async def update_event(event_id: str, event: Event):
    update_doc = event.dict()
    update_doc["updated_at"] = datetime.utcnow()

    result = await db.events.update_one(
        {"_id": to_object_id(event_id)},
        {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"message": "Event updated"}

# Delete/events/{event_id}; delete an event by id
# deletes the event with the specified id from the database
@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    result = await db.events.delete_one({"_id": to_object_id(event_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"message": "Event deleted"}

# -- Attendees
# Post/attendees; create a new attendee
# a new attendee is created with the provided details and stored in the database
# if successful, returns the id of the created attendee
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    attendee_doc = attendee.dict()
    attendee_doc["created_at"] = datetime.utcnow()
    result = await db.attendees.insert_one(attendee_doc)
    return {"message": "Attendee created", "id": str(result.inserted_id)}

# Get/attendees; retrieve all attendees
# fetches up to a 100 attendees from the database and returns them as a list
@app.get("/attendees")
async def get_attendees():
    attendees = await db.attendees.find().to_list(100)
    return [stringify_id(a) for a in attendees]

# Get/attendees/{attendee_id}; retrieve a specific attendee by id
# fetches the attendee with the specified id from the database
# if attendee is found, returns the attendee details
# if the attendee is not found, returns a 404 error
@app.get("/attendees/{attendee_id}")
async def get_attendee(attendee_id: str):
    doc = await db.attendees.find_one({"_id": to_object_id(attendee_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return stringify_id(doc)

# Put/attendees/{attendee_id}; update an existing attendee by id
# updates the attendee with the specified id using the provided details
@app.put("/attendees/{attendee_id}")
async def update_attendee(attendee_id: str, attendee: Attendee):
    update_doc = attendee.dict()
    update_doc["updated_at"] = datetime.utcnow()

    result = await db.attendees.update_one(
        {"_id": to_object_id(attendee_id)},
        {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")

    return {"message": "Attendee updated"}

# Delete/attendees/{attendee_id}; delete an attendee by id
# deletes the attendee with the specified id from the database
@app.delete("/attendees/{attendee_id}")
async def delete_attendee(attendee_id: str):
    result = await db.attendees.delete_one({"_id": to_object_id(attendee_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")

    return {"message": "Attendee deleted"}


# -- Venues
# Post/venues; create a new venue
# a new venue is created with the provided details and stored in the database
# if successful, returns the id of the created venue
@app.post("/venues")
async def create_venue(venue: Venue):
    venue_doc = venue.dict()
    venue_doc["created_at"] = datetime.utcnow()
    result = await db.venues.insert_one(venue_doc)
    return {"message": "Venue created", "id": str(result.inserted_id)}

# Get/venues; retrieve all venues
# fetches up to a 100 venues from the database and returns them as a list
@app.get("/venues")
async def get_venues():
    venues = await db.venues.find().to_list(100)
    return [stringify_id(v) for v in venues]

# Get/venues/{venue_id}; retrieve a specific venue by id
# fetches the venue with the specified id from the database
# if venue is found, returns the venue details
# if the venue is not found, returns a 404 error
@app.get("/venues/{venue_id}")
async def get_venue(venue_id: str):
    doc = await db.venues.find_one({"_id": to_object_id(venue_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Venue not found")
    return stringify_id(doc)

# PUT /venues/{venue_id}; update an existing venue by id
# updates the venue with the specified id using the provided details
@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, venue: Venue):
    update_doc = venue.dict()
    update_doc["updated_at"] = datetime.utcnow()

    result = await db.venues.update_one(
        {"_id": to_object_id(venue_id)},
        {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")

    return {"message": "Venue updated"}

# DELETE /venues/{venue_id}; delete a venue by id
# deletes the venue with the specified id from the database
@app.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str):
    result = await db.venues.delete_one({"_id": to_object_id(venue_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")

    return {"message": "Venue deleted"}

# -- Bookings
# Post/bookings; create a new booking
# a new booking is created with the provided details and stored in the database
# if successful, returns the id of the created booking
@app.post("/bookings")
async def create_booking(booking: Booking):
    booking_doc = booking.dict()
    booking_doc["created_at"] = datetime.utcnow()
    result = await db.bookings.insert_one(booking_doc)
    return {"message": "Booking created", "id": str(result.inserted_id)}

# Get/bookings; retrieve all bookings
# fetches up to a 100 bookings from the database and returns them as a list
@app.get("/bookings")
async def get_bookings():
    bookings = await db.bookings.find().to_list(100)
    return [stringify_id(b) for b in bookings]

# Get/bookings/{booking_id}; retrieve a specific booking by id
# fetches the booking with the specified id from the database
# if booking is found, returns the booking details
# if the booking is not found, returns a 404 error
@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    doc = await db.bookings.find_one({"_id": to_object_id(booking_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return stringify_id(doc)

# PUT /bookings/{booking_id}; update an existing booking by id
# updates the booking with the specified id using the provided details
@app.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, booking: Booking):
    update_doc = booking.dict()
    update_doc["updated_at"] = datetime.utcnow()

    result = await db.bookings.update_one(
        {"_id": to_object_id(booking_id)},
        {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {"message": "Booking updated"}


# DELETE /bookings/{booking_id}; delete a booking by id
# deletes the booking with the specified id from the database
@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str):
    result = await db.bookings.delete_one({"_id": to_object_id(booking_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {"message": "Booking deleted"}

# -- Media Upload + Retrieve
# Post/upload_event_poster/{event_id}; upload an iamge file to be used as an event poster
# the event_id in the URL links the poster top a specific event

# How it works:
# - The file is recieved using multipart/form-data via UploadFile
# - The binary content of the file is read asynchronously
# - A file is stored directly in the MongoDB "multimedia" collection

# Database ineraction:
# - Inserts a document into the multimedia collection
# - Stores both binary content and metadata (filename, content type, related event id, upload timestamp)

# This returns the id of the stored file document upon successful upload
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

# Post/upload_promo_video/{event_id}; upload a video file to be used as a promotional video for an event
# the event_id in the URL links the video to a specific event 

# How it works:
# - The file is recieved using multipart/form-data via UploadFile
# - Read and store the binary video in MongoDB

# Database interaction:
# - Stores the video file in the multimedia collection.
# - Uses the event_id to link the video to the relevant event.

# This returns the id of the stored video document upon successful upload
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

# Post/upload_venue_photo/{venue_id}; upload an image file to be used as a venue photo
# the venue_id in the URL links the photo to a specific venue

# How it works:
# - The file is recieved using multipart/form-data via UploadFile
# - Stores the binary image data and metadata in MongoDB

# Database interaction:
# - Inserts the venue photo into the multimedia collection.
# - The venue_id links the photo to a specific venue.

# This returns the id of the stored photo document upon successful upload
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
