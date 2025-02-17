import os
import json
import base64
import uuid
import bcrypt
import jwt
import redis
import docx
from io import BytesIO
from datetime import datetime, timedelta
from flask_session import Session
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image

from image_processing.objDec import detect  # your custom object detection module

load_dotenv()

app = Flask(__name__)
CORS(app)  # For production, restrict this to trusted origins
# Flask-Session Configuration (Uses Filesystem Instead of Redis)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', "flask_session_key:b18db5ee-af5b-43ca-a58f-777312ba50aa")
app.config['SESSION_TYPE'] = 'filesystem'  # Ensure sessions are stored as files
app.config['SESSION_FILE_DIR'] = './sessions'  # Directory for storing session files
app.config['SESSION_PERMANENT'] = True  # Keep session valid
app.config['SESSION_USE_SIGNER'] = True  # Secure sessions with signing
app.config['SESSION_KEY_PREFIX'] = 'session:'  # Prefix to differentiate session keys
app.config['SESSION_COOKIE_NAME'] = 'flask_session'  # Custom cookie name
Session(app)
print(app.config['SECRET_KEY'])
# MongoDB connection
URI = os.getenv('USER1')
client = MongoClient(URI, server_api=ServerApi('1'))
try:
    client.admin.command('ping')
    db = client["beproject"]
    print("Successfully connected to MongoDB!")
except Exception as e:
    print("MongoDB connection error:", e)

# Database collections by entity type
users_collection = db["users"]
exams_collection = db["exams"]
logs_collection = db["logs"]

# Directories for file storage
UPLOAD_FOLDER = 'uploaded_files'
FRAME_DIR = "received_frames"
CODE_DIR = "received_codes"

for directory in [UPLOAD_FOLDER, FRAME_DIR, CODE_DIR]:
    os.makedirs(directory, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_EXTENSIONS = {'.txt', '.docx'}

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

# {
#     "phoneConnected": False,
#     "lastPhonePing": None,
#     "tabActive": True
# }

@app.route('/mobile-monitor', methods=['GET'])
def mobile_monitor():
    exam_id = request.args.get('examId')
    session_token = request.args.get('sessionToken')

    if not exam_id or not session_token:
        return jsonify({"success": False, "message": "Missing examId or sessionToken"}), 400

    print(f"Checking session for examId: {exam_id}, sessionToken: {session_token}")  # Debugging line
    print(f"Current session data: {dict(session)}")  # Print all session data

    # Check if session exists
    for username, session_data in session.items():
        if (
            isinstance(session_data, dict) and
            session_data.get("sessionToken") == session_token and
            session_data.get("examId") == exam_id
        ):
            return jsonify({"success": True, "message": "Session is active"}), 200

    return jsonify({"success": False, "message": "Invalid or expired session"}), 403


    return jsonify({"success": False}), 404


# Mobile ping to update session activity
@app.route('/mobile/ping', methods=['POST'])
def mobile_ping():
    session_token = request.args.get('token')

    for username, session_data in session.items():
        if session_data.get("sessionToken") == session_token:
            session_data["lastPhonePing"] = datetime.utcnow().isoformat()
            return jsonify({"success": True})

    return jsonify({"success": False}), 404

@app.route('/exam/start', methods=['POST'])
def start_exam_session():
    data = request.get_json()
    exam_id = data.get("examId")
    username = data.get("username")

    if not exam_id or not username:
        return jsonify({"success": False, "message": "Missing examId or username"}), 400

    # Check if the user already has an active session
    if session.get(username):
        return jsonify({"success": False, "message": "An active exam session already exists"}), 409

    # Generate session token and store in session
    session_token = str(uuid.uuid4())
    session[username] = {
        "examId": exam_id,
        "sessionToken": session_token,
        "expires": (datetime.utcnow() + timedelta(days=1)).isoformat()
    }

    print(f"Session stored: {session[username]}")  # Debugging line

    return jsonify({"success": True, "message": "Exam session started", "sessionToken": session_token}), 200


# Exam session end endpoint
@app.route('/exam/end', methods=['POST'])
def end_exam_session():
    data = request.get_json()
    username = data.get("username")

    if username in session:
        session.pop(username, None)  # Remove session data
        return jsonify({"success": True, "message": "Exam session ended"}), 200
    
    return jsonify({"success": False, "message": "No active session found"}), 404

@app.route('/upload', methods=['POST'])
def upload_frame():
    data = request.get_json()
    image_data = data.get('image')
    if not image_data:
        return jsonify({"success": False, "message": "No image provided"}), 400

    try:
        # Remove data URI prefix if present
        if "," in image_data:
            image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
        img = Image.open(BytesIO(image_bytes))
        objects = detect(img)
        return jsonify({"success": True, "objects": objects}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error processing image: {str(e)}"}), 500

@app.route('/submit-code', methods=['POST'])
def submit_code():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    question_number = data.get('question_number', 1)

    if not code:
        return jsonify({"success": False, "message": "No code provided"}), 400
    if not language:
        return jsonify({"success": False, "message": "No language specified"}), 400

    try:
        filename = f"{language}_question_{question_number}.txt"
        file_path = os.path.join(CODE_DIR, filename)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(code)
        return jsonify({"success": True, "message": f"Code for question {question_number} saved successfully as {filename}"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving code: {str(e)}"}), 500

@app.route('/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Unsupported file type. Only .txt and .docx are allowed."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        exam_name = request.form.get('name')
        exam_duration = request.form.get('duration')
        exam_date = request.form.get('date')

        result = parse_questions(filepath, filename)
        exam_id = result["examId"]
        questions = result["questions"]

        # If exam details are provided, store exam data in a dedicated collection
        if exam_name and exam_duration and exam_date:
            exam_data = {
                "id": exam_id,
                "name": exam_name,
                "duration": exam_duration,
                "date": exam_date,
                "questions": questions
            }
            exams_collection.insert_one(exam_data)
            return jsonify({"success": True, "examId": exam_id}), 200
        else:
            return jsonify({"success": True, "questions": questions}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error processing file: {str(e)}"}), 500

@app.route('/exam/create', methods=['POST'])
def create_exam():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Unsupported file type. Only .txt and .docx are allowed."}), 400

    exam_name = request.form.get('name')
    exam_duration = request.form.get('duration')
    exam_date = request.form.get('date')

    if not exam_name or not exam_duration or not exam_date:
        return jsonify({"success": False, "message": "Missing exam details (name, duration, date)."}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        result = parse_questions(filepath, filename)
        questions = result["questions"]
        if not questions:
            return jsonify({"success": False, "message": "No valid questions found in the file."}), 400
        
        exam_id = str(uuid.uuid4())
        exam_data = {
            "id": exam_id,
            "name": exam_name,
            "duration": exam_duration,
            "date": exam_date,
            "questions": questions
        }
        exams_collection.insert_one(exam_data)
        return jsonify({"success": True, "examId": exam_id}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error processing file: {str(e)}"}), 500

@app.route('/store-keylogs', methods=['POST'])
def store_keylogs():
    data = request.get_json()
    key_logs = data.get('keyLogs', '')
    if not key_logs:
        return jsonify({"success": False, "message": "No key logs provided"}), 400
    try:
        log_entry = {
            "timestamp": datetime.utcnow(),
            "keyLogs": key_logs
        }
        logs_collection.insert_one(log_entry)
        return jsonify({"success": True, "message": "Keylogs stored successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error storing keylogs: {str(e)}"}), 500

def parse_questions(filepath, filename, uid=None):
    if uid is None:
        uid = str(uuid.uuid4())
    questions = []
    content = ""
    if filename.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    elif filename.endswith('.docx'):
        doc = docx.Document(filepath)
        content = "\n".join([p.text for p in doc.paragraphs])
    
    lines = content.split('\n')
    current_question = None
    current_options = []
    question_type = 'mcq'
    for line in lines:
        line = line.strip()
        if 'Problem Statement:' in line:
            if current_question:
                questions.append({"type": question_type, "question": current_question, "options": current_options})
            current_question = line
            current_options = []
            question_type = 'coding'
        elif line.endswith('?'):
            if current_question:
                questions.append({"type": question_type, "question": current_question, "options": current_options})
            current_question = line
            current_options = []
            question_type = 'mcq'
        elif line.startswith(('a)', 'b)', 'c)', 'd)')) and question_type == 'mcq':
            current_options.append(line)
    if current_question:
        questions.append({"type": question_type, "question": current_question, "options": current_options})
    return {"examId": uid, "questions": questions}

@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"success": False, "message": "File is too large. Maximum size allowed is 10MB."}), 413

@app.route('/auth/signup', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        required_fields = ["username", "password", "email", "role"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Missing {field} field"}), 400
        
        username = data["username"]
        password = data["password"]
        email = data["email"]
        role = data["role"]

        if users_collection.find_one({"username": username}):
            return jsonify({"success": False, "message": "Username already exists"}), 409
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        JWT_SECRET = os.getenv("JWT_SECRET")
        token_payload = {
            "username": username,
            "email": email,
            "role": role,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
        users_collection.insert_one({
            "username": username,
            "password": hashed_password,
            "email": email,
            "role": role
        })
        return jsonify({"success": True, "message": "User registered successfully", "token": token}), 201
    except Exception as e:
        return jsonify({"success": False, "message": "An error occurred during signup"}), 500

@app.route('/auth/login', methods=['POST'])
def authenticate_user():
    try:
        data = request.get_json()
        if "username" not in data or "password" not in data:
            return jsonify({"success": False, "message": "Missing username or password"}), 400

        username = data["username"]
        user_password = data["password"]
        JWT_SECRET = os.getenv("JWT_SECRET")
        
        user_data = users_collection.find_one({"username": username})
        if user_data:
            if not bcrypt.checkpw(user_password.encode('utf-8'), user_data['password']):
                return jsonify({"success": False, "message": "Invalid credentials"}), 401
            token_payload = {
                "username": user_data['username'],
                "email": user_data['email'],
                "role": user_data['role'],
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=1)
            }
            token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
            return jsonify({"success": True, "message": "Login successful", "token": token}), 200
        else:
            return jsonify({"success": False, "message": "User not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": "An error occurred during login"}), 500

@app.route('/auth/verify', methods=['GET'])
def verify_token():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"success": False, "message": "Token is missing"}), 401
        token = auth_header.split(" ")[1]
        JWT_SECRET = os.getenv("JWT_SECRET")
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return jsonify({
            "success": True,
            "message": "Token is valid",
            "user_data": {"username": decoded_token['username'], "role": decoded_token['role']}
        }), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"success": False, "message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": "An error occurred during token verification"}), 500

@app.route('/exam/details/<exam_id>', methods=['GET'])
def get_exam_details(exam_id):
    exam_doc = exams_collection.find_one({"id": exam_id}, {"_id": 0})
    if exam_doc:
        try:
            duration = int(exam_doc.get("duration"))
        except:
            duration = 0
        return jsonify({
            "success": True,
            "questions": exam_doc.get("questions", []),
            "duration": duration
        }), 200
    return jsonify({"success": False, "message": "Exam not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
