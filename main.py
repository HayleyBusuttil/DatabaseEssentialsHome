from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from dotenv import load_dotenv
import motor.motor_asyncio
import io
import os

from bson import ObjectId

# Load environment variables from .env file
load_dotenv()

#create FastAPI instance
app = FastAPI(title="Event Management API")

# -- Database Connection
# Connect to MongoDB Atlas adn read the MONGO_URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not found. Make sure you created a .env file in the project root.")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI) # create mongoDB client using motor(async driver)
db = client.event_management  #select the database

# -- Helpers

def to_object_id(id_str: str) -> ObjectId:
    # to_object_id is used to convert a string to a MongoDB ObjectId
    # why: 
    # MonogDb document IDs are stored as ObjectId and not plain strings
    # to query by _id, we need to convert the string to ObjectId
    # validation on the formar of the string is also performed to prevent injection attacks
    if not ObjectId.is_valid(id_str):
        # HTTP 400 is raised for invalid ID formats
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return ObjectId(id_str)

def stringify_id(doc: dict) -> dict:
    # stringify_id is used to convert the ObjectId in a document to a string for JSON responses
    # why:
    # MongoDB returns _id as an ObjectId, which is not JSON serializable (FastAPI uses JSON for responses)
    # This function modifies the document in place and returns it
    doc["_id"] = str(doc["_id"])
    return doc

# -- Pydantic Data Models

# pydantic models are used to vlaidate and santize user input. They help prevent injectrion attacks as they 
# enforce strict datatypes, reject unexpected or extra fields and apply length and value constrains 

class Event(BaseModel):
    # Request model for creating or updating an event
    model_config = ConfigDict(extra="forbid")  # Forbid extra fields not defined in the model
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=0, max_length=1000)
    date: str = Field (min_length=4 , max_length=50) # YYYY-MM-DD 
    venue_id: str = Field(min_length=24, max_length=24)  # MongoDB ObjectId length
    max_attendees: int = Field(ge=1, le=100000)  # Greater than 0 and less than 100,000

class Attendee(BaseModel):
    # Request model for creating or updating an attendee
    model_config = ConfigDict(extra="forbid")  # Forbid extra fields not defined in the model
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr # Pydantic's built-in email type for validation
    phone: Optional[str] = Field(default=None, max_length=30)

class Venue(BaseModel):
    # Request model for creating or updating a venue
    model_config = ConfigDict(extra="forbid")  # Forbid extra fields not defined in the model
    name: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=5, max_length=300)
    capacity: int = Field(ge=1, le=100000)

class Booking(BaseModel):
    # Request model for creating a booking
    model_config = ConfigDict(extra="forbid")  # Forbid extra fields not defined in the model
    # Ids are validated by length before ObjectId conversion
    event_id: str = Field(min_length=24, max_length=24)
    attendee_id: str = Field(min_length=24, max_length=24)
    ticket_type: Literal["standard", "vip", "student"] # Literal restricts to specified values only
    quantity: int = Field(ge=1, le=20)


# -- Root Endpoint
# Quick test endpoint to verify API is running was used for initial testing
@app.get("/")
async def root():
    return {"message": "API is running"}


# -- API Endpoints

# -- Events
@app.post("/events")
# Post/events; create a new event
# a new event is created with the provided details and stored in the database
# DB interaction:
# - Inserts a new document into the events collection (db.events.insert_one(event_doc))
# if successful, returns the id of the created event (as a string)
async def create_event(event: Event):
    event_doc = event.dict()
    event_doc["created_at"] = datetime.utcnow()
    result = await db.events.insert_one(event_doc)
    return {"message": "Event created", "id": str(result.inserted_id)}

@app.get("/events")
# Get/events; retrieve all events
# fetches up to a 100 events from the database and returns them as a list
# DB interaction:
# - Finds documents in the events collection (db.events.find())
# - Converts the cursor to a list with a limit of 100 documents (to_list(100))
# returns a list of events with their _id fields converted to strings
async def get_events():
    events = await db.events.find().to_list(100)
    return [stringify_id(e) for e in events]

@app.get("/events/{event_id}")
# Get/events/{event_id}; retrieve a specific event by id
# fetches the event with the specified id from the database
# DB interaction:
# - Finds a document in the events collection by _id (db.events.find_one({"_id": ObjectId(event_id)}))
# if event is found, returns the event details
# Errors:
# 400 - raised for invalid ID formats
# 404 - raised when event with specified ID is not found
async def get_event(event_id: str):
    doc = await db.events.find_one({"_id": to_object_id(event_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return stringify_id(doc)

@app.put("/events/{event_id}")
# Put/events/{event_id}; update an existing event by id
# updates the event with the specified id using the provided details
# DB interaction:
# - Updates a document in the events collection by _id (db.events.update_one({"_id": ObjectId(event_id)}, {"$set": update_doc}))
# if successful, returns a message indicating the event was updated
# Errors:
# 404 - raised if no matching document exists to update
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

@app.delete("/events/{event_id}")
# Delete/events/{event_id}; delete an event by id
# deletes the event with the specified id from the database
# DB interaction:
# - Deletes a document from the events collection by _id (db.events.delete_one({"_id": ObjectId(event_id)}))
# if successful, returns a message indicating the event was deleted
# Errors:
# 404 - raised if no matching document exists to delete
async def delete_event(event_id: str):
    result = await db.events.delete_one({"_id": to_object_id(event_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"message": "Event deleted"}


# -- Attendees
@app.post("/attendees")
# Post/attendees; create a new attendee
# a new attendee is created with the provided details and stored in the database
# DB interaction:
# - Inserts a new document into the attendees collection (db.attendees.insert_one(attendee_doc))
# if successful, returns the id of the created attendee
async def create_attendee(attendee: Attendee):
    attendee_doc = attendee.dict()
    attendee_doc["created_at"] = datetime.utcnow()
    result = await db.attendees.insert_one(attendee_doc)
    return {"message": "Attendee created", "id": str(result.inserted_id)}

@app.get("/attendees")
# Get/attendees; retrieve all attendees
# fetches up to a 100 attendees from the database and returns them as a list
# DB interaction:
# - Finds documents in the attendees collection (db.attendees.find())
# - Converts the cursor to a list with a limit of 100 documents (to_list(100))
# returns a list of attendees with their _id fields converted to strings
async def get_attendees():
    attendees = await db.attendees.find().to_list(100)
    return [stringify_id(a) for a in attendees]

@app.get("/attendees/{attendee_id}")
# Get/attendees/{attendee_id}; retrieve a specific attendee by id
# fetches the attendee with the specified id from the database
# DB interaction:
# - Finds a document in the attendees collection by _id (db.attendees.find_one({"_id": ObjectId(attendee_id)}))
# if attendee is found, returns the attendee details
# Errors:
# 400 - raised for invalid ID formats
# 404 - raised if no matching document exists
async def get_attendee(attendee_id: str):
    doc = await db.attendees.find_one({"_id": to_object_id(attendee_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return stringify_id(doc)

@app.put("/attendees/{attendee_id}")
# Put/attendees/{attendee_id}; update an existing attendee by id
# updates the attendee with the specified id using the provided details
# DB interaction:
# - Updates a document in the attendees collection by _id (db.attendees.update_one({"_id": ObjectId(attendee_id)}, {"$set": update_doc}))
# if successful, returns a message indicating the attendee was updated
# Errors:
# 404 - raised if no matching document exists to update
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

@app.delete("/attendees/{attendee_id}")
# Delete/attendees/{attendee_id}; delete an attendee by id
# deletes the attendee with the specified id from the database
# DB interaction:
# - Deletes a document from the attendees collection by _id (db.attendees.delete_one({"_id": ObjectId(attendee_id)}))
# if successful, returns a message indicating the attendee was deleted
# Errors:
# 404 - raised if no matching document exists to delete
async def delete_attendee(attendee_id: str):
    result = await db.attendees.delete_one({"_id": to_object_id(attendee_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")

    return {"message": "Attendee deleted"}


# -- Venues
@app.post("/venues")
# Post/venues; create a new venue
# a new venue is created with the provided details and stored in the database
# DB interaction:
# - Inserts a new document into the venues collection (db.venues.insert_one(venue_doc))
# if successful, returns the id of the created venue
async def create_venue(venue: Venue):
    venue_doc = venue.dict()
    venue_doc["created_at"] = datetime.utcnow()
    result = await db.venues.insert_one(venue_doc)
    return {"message": "Venue created", "id": str(result.inserted_id)}

@app.get("/venues")
# Get/venues; retrieve all venues
# fetches up to a 100 venues from the database and returns them as a list
# DB interaction:
# - Finds documents in the venues collection (db.venues.find())
# - Converts the cursor to a list with a limit of 100 documents (to_list(100))
# if successful, returns a list of venues with their _id fields converted to strings
async def get_venues():
    venues = await db.venues.find().to_list(100)
    return [stringify_id(v) for v in venues]

@app.get("/venues/{venue_id}")
# Get/venues/{venue_id}; retrieve a specific venue by id
# fetches the venue with the specified id from the database
# DB interaction:
# - Finds a document in the venues collection by _id (db.venues.find_one({"_id": ObjectId(venue_id)}))
# if venue is found, returns the venue details
# Eorros:
# 400 - raised for invalid ID formats
# 404 - raised when venue with specified ID is not found
async def get_venue(venue_id: str):
    doc = await db.venues.find_one({"_id": to_object_id(venue_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Venue not found")
    return stringify_id(doc)

@app.put("/venues/{venue_id}")
# PUT /venues/{venue_id}; update an existing venue by id
# updates the venue with the specified id using the provided details
# DB interaction:
# - Updates a document in the venues collection by _id (db.venues.update_one({"_id": ObjectId(venue_id)}, {"$set": update_doc}))
# if successful, returns a message indicating the venue was updated
# Errors:
# 404 - raised if no matching document exists to update
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

@app.delete("/venues/{venue_id}")
# DELETE /venues/{venue_id}; delete a venue by id
# deletes the venue with the specified id from the database
# DB interaction:
# - Deletes a document from the venues collection by _id (db.venues.delete_one({"_id": ObjectId(venue_id)}))
# if successful, returns a message indicating the venue was deleted
# Errors:
# 404 - raised if no matching document exists to delete
async def delete_venue(venue_id: str):
    result = await db.venues.delete_one({"_id": to_object_id(venue_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")

    return {"message": "Venue deleted"}


# -- Bookings
@app.post("/bookings")
# Post/bookings; create a new booking
# a new booking is created with the provided details and stored in the database
# DB interaction:
# - Inserts a new document into the bookings collection (db.bookings.insert_one(booking_doc))
# if successful, returns the id of the created booking
async def create_booking(booking: Booking):
    booking_doc = booking.dict()
    booking_doc["created_at"] = datetime.utcnow()
    result = await db.bookings.insert_one(booking_doc)
    return {"message": "Booking created", "id": str(result.inserted_id)}

@app.get("/bookings")
# Get/bookings; retrieve all bookings
# fetches up to a 100 bookings from the database and returns them as a list
# DB interaction:
# - Finds documents in the bookings collection (db.bookings.find())
# - Converts the cursor to a list with a limit of 100 documents (to_list(100))
# returns a list of bookings with their _id fields converted to strings
async def get_bookings():
    bookings = await db.bookings.find().to_list(100)
    return [stringify_id(b) for b in bookings]

@app.get("/bookings/{booking_id}")
# Get/bookings/{booking_id}; retrieve a specific booking by id
# fetches the booking with the specified id from the database
# DB interaction:
# - Finds a document in the bookings collection by _id (db.bookings.find_one({"_id": ObjectId(booking_id)}))
# if booking is found, returns the booking details
# Errors:
# 400 - raised for invalid ID formats
# 404 - raised if the booking is not found
async def get_booking(booking_id: str):
    doc = await db.bookings.find_one({"_id": to_object_id(booking_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return stringify_id(doc)

@app.put("/bookings/{booking_id}")
# PUT /bookings/{booking_id}; update an existing booking by id
# updates the booking with the specified id using the provided details
# DB interaction:
# - Updates a document in the bookings collection by _id (db.bookings.update_one({"_id": ObjectId(booking_id)}, {"$set": update_doc}))
# if successful, returns a message indicating the booking was updated
# Errors:
# 404 - raised if no matching document exists to update
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

@app.delete("/bookings/{booking_id}")
# DELETE /bookings/{booking_id}; delete a booking by id
# deletes the booking with the specified id from the database
# DB interaction:
# - Deletes a document from the bookings collection by _id (db.bookings.delete_one({"_id": ObjectId(booking_id)}))
# if successful, returns a message indicating the booking was deleted
# Errors:
# 404 - raised if no matching document exists to delete
async def delete_booking(booking_id: str):
    result = await db.bookings.delete_one({"_id": to_object_id(booking_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {"message": "Booking deleted"}


# -- Media Upload + Retrieve
@app.post("/upload_event_poster/{event_id}")
# Post/upload_event_poster/{event_id}; upload an iamge file to be used as an event poster
# the event_id in the URL links the poster top a specific event

# How it works:
# - The file is recieved using multipart/form-data via UploadFile
# - The binary content of the file is read asynchronously
# - A file is stored directly in the MongoDB "multimedia" collection

# DB interaction:
# - Inserts a document into the multimedia collection
# - Stores both binary content and metadata (filename, content type, related event id, upload timestamp)

# This returns the id of the stored file document upon successful upload
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
# Post/upload_promo_video/{event_id}; upload a video file to be used as a promotional video for an event
# the event_id in the URL links the video to a specific event 

# How it works:
# - The file is recieved using multipart/form-data via UploadFile
# - Read and store the binary video in MongoDB

# DB interaction:
# - Stores the video file in the multimedia collection.
# - Uses the event_id to link the video to the relevant event.

# This returns the id of the stored video document upon successful upload
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
# Post/upload_venue_photo/{venue_id}; upload an image file to be used as a venue photo
# the venue_id in the URL links the photo to a specific venue

# How it works:
# - The file is recieved using multipart/form-data via UploadFile
# - Stores the binary image data and metadata in MongoDB

# DB interaction:
# - Inserts the venue photo into the multimedia collection.
# - The venue_id links the photo to a specific venue.

# This returns the id of the stored photo document upon successful upload
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
# GET /media/{media_id}; retrieve a media file by id
# retrieves the media file with the specified id from the database and streams it back to the client

# How it works:
# - Finds the media document in the multimedia collection by _id
# - If found, streams the binary content back using StreamingResponse (StreamingResponse was used to handel videos and allows postman to render or download the file correctly)

# DB interaction:
# - Finds a document in the multimedia collection by _id (db.multimedia.find_one({"_id": ObjectId(media_id)}))
# if found, streams the file content with appropriate content type and filename headers

# Errors:
# 404 - raised if the file is not found 
async def get_media(media_id: str):
    doc = await db.multimedia.find_one({"_id": to_object_id(media_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    return StreamingResponse(
        io.BytesIO(doc["content"]),
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'inline; filename="{doc["filename"]}"'}
    )
