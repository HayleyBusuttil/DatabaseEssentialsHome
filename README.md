## Database Essentials Home Assigment - Event Managemnet API
Repository Name - DatabaseEssentialsHome 

# Enviorment Setup 
A python virtual enviorment was created to isolate any project dependencies.

# Installation of virtual enviorment:
(in Terminal)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installed project dependencies 
All the installed python dependencies are listed in the requirments.txt file. 
- FastAPI
- Unvicorn
- motor
- Pydantic
- Python-dotenv
- Requests

# gitignore
A gitignore fiel was created to exclude files and folders thaty should not be commited to teh repository:
- The Python virtual enviorement (.venv)
- Enviorment variable file (.env)
- Any python cache files. 

# Task 2 - Schema Design
MongoDB schema was designed using multiple collections. Seperate collections were created for events, attendees, venues, bookings and multimedia assets. Each collection represents sepcific concepts in teh system.