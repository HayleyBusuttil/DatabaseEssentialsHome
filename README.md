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

# .gitignore
A gitignore fiel was created to exclude files and folders thaty should not be commited to teh repository:
- The Python virtual enviorement (.venv)
- Enviorment variable file (.env)
- Any python cache files. 

# Task 2 - Database schema
MongoDB schema was designed using multiple collections. Seperate collections were created for events, attendees, venues, bookings and multimedia assets. Each collection represents sepcific concepts in the system.
Relationships between entities were implemneted useing ObjectId references. 
The Schema was deployed on MongoDB Atlas and populated with mock data using Datagrip. 

# Task 3 - Development of Web API

# Enviorment Variables
A .env file is used to store the enviorment variables needed for the application, such as the MongoDB connection string. This helps to keep sensitive information seperate from the main source code. The .env file is executed from the repository using the .gitignore.

# Installed Libraries
The required python dependencies are listed in the requiremnts.txt file:
- python-mulitpart 
This is a package that is required to handle the file uploads of the mulitmedia functionality, including event posters, promotional videos and venue photos. 
Freezed the depencies into the requirements.txt file using pip freeze > requirements.txt

# Local Development and Testing
The FastAPI was used to develop and run APIs locally using Uvicorn. The application runs on http://127.0.0.1:8000 , 
Swagger documentation is provided at: http://127.0.0.1:8000/docs.
To run the API locally, the following command was used:
unvicorn mian:app --reload

Postman was used to test the endpoints as outlined in Appendix E. This included testing for and creating events, attendees, venues, and bookings. Also uploading and retrieving event posters, promotional videos and venue photos. 

# Deploying 
- Created vercel.json file in the project root to configure the Vercel deployment.
- Pushed the project to github.
- Created a new project on Vercel, imported the Github repo and deployed the project through the Vercel dashboard.
- After depolymentment attached Eviorment Varibale (Mongo URI) in the project settigns of Vercel.
- Redepolyed the project from dashboard.

# Task 4 - Configure Database Security

# Setting Appropriate Credentials:
A secure satabase user was created in MongoDB Atlas specifically for the Event Management API. The user uses password-based authentication (SCRAM) with a strong, auto-generated password.
The database user was configured using the principle of least privilege. Instead of assigning broad administrative roles, the user was granted readWrite access limited to the event_management database only.

Redeployment of the app had to be done on 13/01/2026 due to git issues

# IP whitelisting
IP whitelisting was configured using MongoDB Atlas Network Access.During development, database access was restricted to my own trusted public IP address. When deploying the API on Vercel, the hosted endpoints (such as /events) required access from dynamic serverless IP addresses.(0.0.0.0/0) was enabled to allow the deployed API to function correctly. 

# SQL injection 
- Pydantic
pip install email-validator (this was installed and sued for email validation)
Added Strict pydantic validation to prevent SQL injection attacks

- ObjectId Validation
all endpoints that require Ids now validate the incoming Id value before using them in queries, this prevents malformed or malicious inputs from being passed into database queries. 