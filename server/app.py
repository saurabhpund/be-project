from flask import Flask, request, jsonify, send_file,send_from_directory
from flask_cors import CORS
import base64
from io import BytesIO
from PIL import Image
import os
from image_processing.objDec import detect
from werkzeug.utils import secure_filename
import docx
import jwt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import bcrypt
import uuid
from dotenv import load_dotenv
import datetime
from dateutil import parser
import re
import librosa
import numpy as np
import pandas as pd
from flask_mail import Mail, Message
import openpyxl
import boto3
from botocore.exceptions import ClientError

load_dotenv()

app = Flask(__name__)

# Configure CORS with more specific settings
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "http://192.168.0.103:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
})

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 587))
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

mail = Mail(app)
# Connect to MongoDB using the URI from environment variables
URI = os.getenv('USER1')
try:
    client = MongoClient(URI, server_api=ServerApi('1'))
    client.admin.command('ping')
    db = client["beproject"]
    print("You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Collection for attempted exams (separate from the users collection)
db_collection = client["beproject"]["attempted_exams"]
db_exams = client["beproject"]["exams"]
# Ensure directories exist
UPLOAD_FOLDER = 'uploaded_files'
FRAME_DIR = "received_frames"
CODE_DIR = "received_codes"
AUDIO_UPLOAD_FOLDER = "uploaded_audio_fragments"


for directory in [UPLOAD_FOLDER, FRAME_DIR, CODE_DIR, AUDIO_UPLOAD_FOLDER]:
    os.makedirs(directory, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limit file size to 10 MB
ALLOWED_EXTENSIONS = {'.txt', '.docx'}
ALLOWED_EXCEL_EXTENSIONS = {'.xlsx', '.xls'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS
def allowed_excel_file(filename):
    """Check if the uploaded file has an allowed extension for Excel student data."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXCEL_EXTENSIONS

def parse_student_excel(filepath):
    """Parses an Excel file containing student data.
       Assumes the first row contains headers, e.g. Name, Username, Email.
    """
    wb = openpyxl.load_workbook(filepath)
    sheet = wb.active
    students = []
    # Skip header row (assumed row 1)
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1] and row[2]:
            student = {"name": row[0], "username": row[1], "email": row[2]}
            students.append(student)
    return students
@app.route('/audio/<path:filename>', methods=['GET'])
def serve_audio(filename):
    file_path = os.path.join(AUDIO_UPLOAD_FOLDER, filename)
    return send_file(file_path, mimetype="audio/webm")
@app.route('/exam/assigned', methods=['GET'])
def exam_assigned():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "message": "Missing username"}), 400
    try:
        # Get all exams from the exams collection
        exams_cursor = db_exams.find({})
        exams = list(exams_cursor)
        # Get the list of exams the student has attempted.
        attempts_cursor = db_collection.find({"username": username})
        attempted_ids = {attempt.get("examId") for attempt in attempts_cursor}
        # Filter out exams that have been attempted.
        unattempted_exams = [exam for exam in exams if exam.get("id") not in attempted_ids]
        # Convert ObjectId to string
        for exam in unattempted_exams:
            exam["_id"] = str(exam["_id"])
        return jsonify({"success": True, "exams": unattempted_exams}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
@app.route('/upload', methods=['POST'])
def upload_frame():
    """Handles uploading and processing an image frame."""
    data = request.get_json()
    image_data = data.get('image')
    if not image_data:
        return jsonify({"success": False, "message": "No image provided"}), 400
    try:
        image_data = image_data.split(",")[1]
        image = base64.b64decode(image_data)
        img = Image.open(BytesIO(image))
        objects = detect(img)
        return jsonify({"success": True, "objects": objects}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error processing image: {str(e)}"}), 500

@app.route('/submit-code', methods=['POST'])
def submit_code():
    """Handles submitting code from the code editor."""
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
        if exam_name and exam_duration and exam_date:
            result = parse_questions(filepath, filename)
            uid = result["examId"]
            questions = result["questions"]
            exam = {
                "id": uid,
                "name": exam_name,
                "duration": exam_duration,
                "date": exam_date,
                "questions": questions
            }
            # Store exam details in the exams collection
            db_exams.insert_one(exam)
            return jsonify({"success": True, "examId": uid}), 200
        else:
            result = parse_questions(filepath, filename)
            questions = result["questions"]
            return jsonify({"success": True, "questions": questions}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error processing file: {str(e)}"}), 500

@app.route('/exam/create', methods=['POST'])
def createExam():
    uid = str(uuid.uuid4())
    try:
        # Ensure exam questions file is provided
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No exam file part in the request"}), 400
        # Check if Excel file for student data is provided

        if 'studentData' not in request.files:
            return jsonify({"success": False, "message": "No Excel file for student data provided."}), 400
        excel_file = request.files['studentData']
        if excel_file.filename == '':
            return jsonify({"success": False, "message": "No student data file selected."}), 400

        if not allowed_excel_file(excel_file.filename):
            return jsonify({"success": False, "message": "Unsupported student data file type. Only .xlsx and .xls are allowed."}), 400
        exam_file = request.files['file']
        if exam_file.filename == '':
            return jsonify({"success": False, "message": "No exam file selected"}), 400
        if not allowed_file(exam_file.filename):
            return jsonify({"success": False, "message": "Unsupported file type. Only .txt and .docx are allowed for exam file."}), 400

        # Retrieve exam details from form data
        exam_name = request.form.get('name')
        exam_duration = request.form.get('duration')
        exam_date = request.form.get('date')
        active_start = request.form.get('active_start')
        active_end = request.form.get('active_end')
        if not exam_name or not exam_duration or not exam_date or not active_start or not active_end:
            return jsonify({"success": False, "message": "Missing exam details (name, duration, date, active_start, active_end)."}), 400

        # Get instructor details from the Authorization header token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"success": False, "message": "Authorization header missing"}), 401

        token = auth_header.split(" ")[1]
        JWT_SECRET = os.getenv("JWT_SECRET")
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        instructor = decoded.get("username")
        if not instructor:
            return jsonify({"success": False, "message": "Instructor information missing in token"}), 401

        # Save the exam questions file
        exam_filename = secure_filename(exam_file.filename)
        exam_filepath = os.path.join(app.config['UPLOAD_FOLDER'], exam_filename)
        exam_file.save(exam_filepath)
        
        student_excel_filename = secure_filename(excel_file.filename)
        student_excel_filepath = os.path.join(app.config['UPLOAD_FOLDER'], student_excel_filename)
        excel_file.save(student_excel_filepath)

        # Parse questions from the file
        questions_result = parse_questions(exam_filepath, exam_filename)
        
        
        questions = questions_result.get("questions")
        if not questions:
            return jsonify({"success": False, "message": "No valid questions found in the exam file."}), 400
        
        students = parse_student_excel(student_excel_filepath)
        # Build exam document with active period details
        exam_doc = {
            "instructor": instructor,
            "id": uid,
            "name": exam_name,
            "duration": exam_duration,
            "date": exam_date,
            "active_start": active_start,
            "active_end": active_end,
            "questions": questions,
            "maxScore": questions_result.get("maxScore")
        }
        db_exams.insert_one(exam_doc)

        # If an Excel file containing student data is provided, process it and send emails
        for student in students:

            try:

                msg = Message(
                    subject=f"New Exam Notification: {exam_name}",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[student["email"]]

                )
                msg.body = (
                    f"Hello {student['name']},\n\n"
                    f"You have been invited to take the exam '{exam_name}'.\n"
                    f"Exam Details:\n"
                    f"Exam ID: {uid}\n"
                    f"Duration: {exam_duration} minutes\n"
                    f"Active From: {active_start}\n"
                    f"Active To: {active_end}\n\n"
                    f"Please be sure to join the exam only during the active period.\n"
                    f"Thank you."
                )
                mail.send(msg)
            except Exception as email_err:
                # Log email errors and continue with the next student.
                print(f"Error sending email to {student['email']}: {email_err}")
        return jsonify({"success": True, "examId": uid}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error processing exam creation: {str(e)}"}), 500


@app.route('/exam/created', methods=['GET'])
def exam_created():
    instructor = request.args.get("instructor")
    if not instructor:
        return jsonify({"success": False, "message": "Missing instructor"}), 400

    exams = list(db_exams.find({"instructor": instructor}))
    for exam in exams:
        exam["_id"] = str(exam["_id"])
    return jsonify({"success": True, "exams": exams}), 200


@app.route('/exam/active', methods=['GET'])
def exam_active():
    import datetime
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        active_exams = []
        exams_cursor = db_exams.find({})
        for exam in exams_cursor:
            active_start = exam.get("active_start")
            active_end = exam.get("active_end")
            if active_start and active_end:
                try:
                    active_start_dt = datetime.datetime.fromisoformat(active_start)
                    if active_start_dt.tzinfo is None:
                        active_start_dt = active_start_dt.replace(tzinfo=datetime.timezone.utc)
                    active_end_dt = datetime.datetime.fromisoformat(active_end)
                    if active_end_dt.tzinfo is None:
                        active_end_dt = active_end_dt.replace(tzinfo=datetime.timezone.utc)
                except Exception as conv_err:
                    print("Conversion error:", conv_err)
                    continue
                if active_start_dt <= now <= active_end_dt:
                    exam["_id"] = str(exam["_id"])
                    active_exams.append(exam)
        return jsonify({"success": True, "exams": active_exams}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/exam/attempts', methods=['GET'])
def exam_attempts():
    exam_id = request.args.get("examId")
    if not exam_id:
        return jsonify({"success": False, "message": "Missing examId"}), 400

    attempts = list(db_collection.find({"examId": exam_id}))
    for attempt in attempts:
        attempt["_id"] = str(attempt["_id"])
        if "submittedAt" in attempt and attempt["submittedAt"]:
            # Only convert if this field is a datetime instance
            if hasattr(attempt["submittedAt"], "isoformat"):
                attempt["submittedAt"] = attempt["submittedAt"].isoformat()
    return jsonify({"success": True, "attempts": attempts}), 200


@app.route('/exam/active/attempts', methods=['GET'])
def active_exam_attempts():
    """
    Returns the list of attempt records for a given exam.
    This route can be used by the instructor dashboard to view, in real time,
    which students are currently attempting the exam.
    """
    exam_id = request.args.get("examId")
    if not exam_id:
        return jsonify({"success": False, "message": "Missing examId"}), 400

    attempts = list(db_collection.find({"examId": exam_id}))
    for attempt in attempts:
        attempt["_id"] = str(attempt["_id"])
        if "startedAt" in attempt and attempt["startedAt"]:
            if hasattr(attempt["startedAt"], "isoformat"):
                attempt["startedAt"] = attempt["startedAt"].isoformat()
        if "submittedAt" in attempt and attempt["submittedAt"]:
            if hasattr(attempt["submittedAt"], "isoformat"):
                attempt["submittedAt"] = attempt["submittedAt"].isoformat()
    return jsonify({"success": True, "attempts": attempts}), 200

@app.route('/exam/submit', methods=['POST'])
def exam_submit():
    data = request.get_json()
    exam_id = data.get("examId")
    username = data.get("username")
    exam_start_time = data.get("examStartTime")
    user_answers = data.get("answers")
    abnormal_audios = data.get("abnormalAudios", [])

    if not exam_id or not username or not exam_start_time or user_answers is None:
        return jsonify({"success": False, "message": "Missing examId, username, examStartTime, or answers"}), 400

    if exam_start_time.endswith("Z"):
        exam_start_time = exam_start_time.replace("Z", "+00:00")
    exam_start_time = parser.isoparse(exam_start_time).isoformat()

    exam_doc = db_exams.find_one({"id": exam_id})
    if not exam_doc:
        return jsonify({"success": False, "message": "Exam not found"}), 404

    exam_details = exam_doc
    questions = exam_details.get("questions", [])
    computed_score = 0
    for idx, question in enumerate(questions):
        if question.get("type") == "mcq":
            correct = question.get("correctAnswer", "").lower().strip() if question.get("correctAnswer") else ""
            user_ans = (user_answers.get(str(idx)) or "").lower().strip()
            if user_ans and user_ans[0] == correct and correct != "":
                computed_score += question.get("score", 2)

    submitted_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    update_data = {
        "examStartTime": exam_start_time,
        "answers": user_answers,
        "score": computed_score,
        "abnormalAudios": abnormal_audios,
        "submittedAt": submitted_at,
        "examName": exam_details.get("name"),
        "examDuration": exam_details.get("duration"),
        "examDate": exam_details.get("date"),
        "maxScore": exam_details.get("maxScore")
    }

    existing_attempt = db_collection.find_one({"examId": exam_id, "username": username})
    if existing_attempt:
        db_collection.update_one({"_id": existing_attempt["_id"]}, {"$set": update_data})
        updated_attempt = db_collection.find_one({"_id": existing_attempt["_id"]})
        updated_attempt["_id"] = str(updated_attempt["_id"])
        if "submittedAt" in updated_attempt and isinstance(updated_attempt["submittedAt"], datetime.datetime):
            updated_attempt["submittedAt"] = updated_attempt["submittedAt"].isoformat()
        if "startedAt" in updated_attempt and isinstance(updated_attempt["startedAt"], datetime.datetime):
            updated_attempt["startedAt"] = updated_attempt["startedAt"].isoformat()
        return jsonify({"success": True, "attempt": updated_attempt}), 200
    else:
        new_attempt = {
            "examId": exam_id,
            "username": username,
            **update_data
        }
        insert_result = db_collection.insert_one(new_attempt)
        new_attempt["_id"] = str(insert_result.inserted_id)
        new_attempt["submittedAt"] = new_attempt["submittedAt"].isoformat()
        return jsonify({"success": True, "attempt": new_attempt}), 200




@app.route('/exam/attempted', methods=['GET'])
def exam_attempted():
    try:
        username = request.args.get("username")
        if not username:
            return jsonify({"success": False, "message": "Missing username"}), 400

        attempts = list(db_collection.find({"username": username}))
        for attempt in attempts:
            attempt["_id"] = str(attempt["_id"])
            if "submittedAt" in attempt and isinstance(attempt["submittedAt"], datetime.datetime):
                attempt["submittedAt"] = attempt["submittedAt"].isoformat()
        return jsonify({"success": True, "attemptedExams": attempts}), 200
    except Exception as e:
        print("Error in /exam/attempted:", e)
        return jsonify({"success": False, "message": str(e)}), 500


# @app.route('/exam/attempted/latest', methods=['GET'])
# def exam_attempted_latest():
#     username = request.args.get("username")
#     if not username:
#         return jsonify({"success": False, "message": "Missing username"}), 400

#     latest_cursor = db_collection.find({"username": username}).sort("_id", -1).limit(1)
#     latest_attempt = list(latest_cursor)
#     if latest_attempt:
#         attempt = latest_attempt[0]
#         attempt["_id"] = str(attempt["_id"])
#         if "submittedAt" in attempt:
#             attempt["submittedAt"] = attempt["submittedAt"].isoformat()
#         return jsonify({"success": True, "latestExam": attempt}), 200
#     else:
#         return jsonify({"success": True, "latestExam": None}), 200

# AWS S3 Configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)
S3_BUCKET = os.getenv('S3_BUCKET_NAME')

@app.route('/store-keylogs', methods=['POST'])
def store_keylogs():
    data = request.get_json()
    key_logs = data.get('keyLogs', '')
    exam_id = data.get('examId')
    username = data.get('username')
    
    if not key_logs or not exam_id or not username:
        return jsonify({"success": False, "message": "Missing required data"}), 400
        
    try:
        # Create a unique filename for S3
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"keylogs/{exam_id}/{username}_{timestamp}.txt"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=filename,
            Body=key_logs,
            ContentType='text/plain'
        )
        
        # Also store in local file for immediate analysis
        file_path = os.path.join(UPLOAD_FOLDER, 'keylogs.txt')
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(key_logs)
            
        return jsonify({
            "success": True, 
            "message": "Keylogs stored successfully",
            "s3_path": filename
        }), 200
        
    except ClientError as e:
        return jsonify({
            "success": False, 
            "message": f"Error storing keylogs in S3: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"Error storing keylogs: {str(e)}"
        }), 500

@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if "audio" not in request.files:
        return jsonify({"success": False, "message": "No audio file provided"}), 400
        
    audio_file = request.files["audio"]
    exam_id = request.form.get("examId")
    token = request.form.get("token")
    
    if not exam_id or not token:
        return jsonify({"success": False, "message": "Missing examId or token"}), 400
        
    try:
        decoded = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        username = decoded.get("username")
        
        # Create a unique filename for S3
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = secure_filename(audio_file.filename)
        s3_filename = f"audio/{exam_id}/{username}_{timestamp}_{original_filename}"
        
        # Upload to S3
        s3_client.upload_fileobj(
            audio_file,
            S3_BUCKET,
            s3_filename,
            ExtraArgs={'ContentType': 'audio/webm'}
        )
        
        # Also save locally for immediate processing
        local_filename = f"{exam_id}_{username}_{timestamp}_{original_filename}"
        file_path = os.path.join(AUDIO_UPLOAD_FOLDER, local_filename)
        audio_file.save(file_path)
        
        # Update the corresponding exam attempt document
        recording_entry = {
            "file": local_filename,
            "s3_path": s3_filename,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        
        db_collection.update_one(
            {"examId": exam_id, "username": username},
            {"$push": {"recordings": recording_entry}}
        )
        
        return jsonify({
            "success": True, 
            "message": "Audio recording stored successfully",
            "recording": recording_entry
        }), 200
        
    except ClientError as e:
        return jsonify({
            "success": False, 
            "message": f"Error storing audio in S3: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"Error storing audio: {str(e)}"
        }), 500

@app.route('/exam/attempted/latest', methods=['GET'])
def latest_attempt():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "message": "Missing username"}), 400
    latest_cursor = db_collection.find({"username": username}).sort("_id", -1).limit(1)
    latest_attempt = list(latest_cursor)
    if latest_attempt:
        attempt = latest_attempt[0]
        attempt["_id"] = str(attempt["_id"])
        if "submittedAt" in attempt:
            attempt["submittedAt"] = attempt["submittedAt"].isoformat()
        return jsonify({"success": True, "latestExam": attempt}), 200
    else:
        return jsonify({"success": True, "latestExam": None}), 200
@app.route('/exam/result', methods=['GET'])
def exam_result():
    username = request.args.get("username")
    exam_id = request.args.get("examId")
    if not exam_id or not username:
        return jsonify({"success": False, "message": "Missing examId or username"}), 400

    # Query the attempted_exams collection for this student's attempt on the given exam
    attempt = db_collection.find_one({"examId": exam_id, "username": username})
    if attempt:
        attempt["_id"] = str(attempt["_id"])
        if "submittedAt" in attempt and isinstance(attempt["submittedAt"], datetime.datetime):
            attempt["submittedAt"] = attempt["submittedAt"].isoformat()
        return jsonify({"success": True, "result": attempt}), 200
    else:
        return jsonify({"success": False, "message": "Exam attempt not found"}), 404

@app.route('/get-keylogs', methods=['GET'])
def get_keylogs():
    exam_id = request.args.get('examId')
    username = request.args.get('username')
    
    if not exam_id or not username:
        return jsonify({"success": False, "message": "Missing examId or username"}), 400
        
    try:
        # List objects in the keylogs directory for this exam and user
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"keylogs/{exam_id}/{username}_"
        )
        
        if 'Contents' not in response:
            return jsonify({"success": False, "message": "No keylogs found"}), 404
            
        # Get the most recent keylog file
        latest_keylog = max(response['Contents'], key=lambda x: x['LastModified'])
        
        # Get the file content
        file_obj = s3_client.get_object(
            Bucket=S3_BUCKET,
            Key=latest_keylog['Key']
        )
        
        keylog_content = file_obj['Body'].read().decode('utf-8')
        
        return jsonify({
            "success": True,
            "keylogs": keylog_content,
            "timestamp": latest_keylog['LastModified'].isoformat()
        }), 200
        
    except ClientError as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving keylogs from S3: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving keylogs: {str(e)}"
        }), 500

@app.route('/exam/monitoring-data', methods=['GET'])
def get_exam_monitoring_data():
    exam_id = request.args.get('examId')
    username = request.args.get('username')
    
    if not exam_id or not username:
        return jsonify({"success": False, "message": "Missing examId or username"}), 400
        
    try:
        # Get keylogs from S3
        keylog_response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"keylogs/{exam_id}/{username}_"
        )
        
        keylogs = []
        if 'Contents' in keylog_response:
            for keylog in keylog_response['Contents']:
                file_obj = s3_client.get_object(
                    Bucket=S3_BUCKET,
                    Key=keylog['Key']
                )
                keylog_content = file_obj['Body'].read().decode('utf-8')
                keylogs.append({
                    'content': keylog_content,
                    'timestamp': keylog['LastModified'].isoformat(),
                    's3_path': keylog['Key']
                })
        
        # Get audio recordings from S3
        audio_response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"audio/{exam_id}/{username}_"
        )
        
        audio_recordings = []
        if 'Contents' in audio_response:
            for audio in audio_response['Contents']:
                audio_recordings.append({
                    's3_path': audio['Key'],
                    'timestamp': audio['LastModified'].isoformat(),
                    'url': s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': S3_BUCKET,
                            'Key': audio['Key']
                        },
                        ExpiresIn=3600  # URL expires in 1 hour
                    )
                })
        
        return jsonify({
            "success": True,
            "keylogs": keylogs,
            "audio_recordings": audio_recordings
        }), 200
        
    except ClientError as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving monitoring data from S3: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error retrieving monitoring data: {str(e)}"
        }), 500

@app.route('/run-diarization', methods=['POST'])
def run_diarization():
    data = request.get_json()
    exam_id = data.get('examId')
    username = data.get('username')
    audio_path = data.get('audioPath')
    
    if not exam_id or not username or not audio_path:
        return jsonify({"success": False, "message": "Missing required parameters"}), 400
        
    try:
        # Download audio file from S3
        local_path = os.path.join(AUDIO_UPLOAD_FOLDER, f"temp_{exam_id}_{username}.wav")
        s3_client.download_file(S3_BUCKET, audio_path, local_path)
        
        # Run diarization
        import librosa
        import numpy as np
        from pyannote.audio import Pipeline
        
        # Load audio file
        audio, sr = librosa.load(local_path, sr=16000)
        
        # Initialize diarization pipeline
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization",
            use_auth_token=os.getenv("HUGGINGFACE_TOKEN")
        )
        
        # Run diarization
        diarization = pipeline({"waveform": audio, "sample_rate": sr})
        
        # Process results
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        
        # Clean up temporary file
        os.remove(local_path)
        
        return jsonify({
            "success": True,
            "segments": segments
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error running diarization: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
