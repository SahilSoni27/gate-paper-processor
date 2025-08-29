import os
import json
from flask import Flask, request, render_template, redirect, url_for, flash
from mysql.connector import connect, Error
from werkzeug.utils import secure_filename
from tk3_parser import process_pdfs  # We will create this from your tk3.py
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecret"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_mysql_connection():
    try:
        return connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    except Error as e:
        print(f"Database connection error: {e}")
        return None


@app.route('/', methods=['GET', 'POST'])
def upload_paper():
    conn = get_mysql_connection()
    if not conn:
        flash("Database connection failed!", "danger")
        return render_template('upload_paper.html', streams=[])

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, code, name FROM gate_streams")
        streams = cursor.fetchall()
    except Error as e:
        flash(f"Database error: {e}", "danger")
        streams = []

    if request.method == 'POST':
        # Validate form data
        if not all(key in request.form for key in ['stream', 'year', 'set_code', 'paper_type']):
            flash("All fields are required!", "danger")
            return redirect(url_for('upload_paper'))

        try:
            stream_id = int(request.form['stream'])
            year = int(request.form['year'])
        except ValueError:
            flash("Invalid stream or year!", "danger")
            return redirect(url_for('upload_paper'))

        set_code = request.form['set_code']
        paper_type = request.form['paper_type']
        subject_id = 1  # default subject

        # Check if files are present
        if 'paper' not in request.files or 'key' not in request.files:
            flash("Both paper and key files are required!", "danger")
            return redirect(url_for('upload_paper'))

        paper_file = request.files['paper']
        key_file = request.files['key']

        # Validate files
        if paper_file.filename == '' or key_file.filename == '':
            flash("Please select both files!", "danger")
            return redirect(url_for('upload_paper'))

        if not (allowed_file(paper_file.filename) and allowed_file(key_file.filename)):
            flash("Only PDF files are allowed!", "danger")
            return redirect(url_for('upload_paper'))

        # Save uploaded files
        paper_filename = secure_filename(paper_file.filename)
        key_filename = secure_filename(key_file.filename)
        paper_path = os.path.join(UPLOAD_FOLDER, paper_filename)
        key_path = os.path.join(UPLOAD_FOLDER, key_filename)

        try:
            paper_file.save(paper_path)
            key_file.save(key_path)
        except Exception as e:
            flash(f"Error saving files: {e}", "danger")
            return redirect(url_for('upload_paper'))

        try:
            # 1️⃣ Insert into gate_papers
            cursor.execute("""
                INSERT INTO gate_papers (year, stream_id, paper_type, set_code)
                VALUES (%s, %s, %s, %s)
            """, (year, stream_id, paper_type, set_code))
            conn.commit()
            paper_id = cursor.lastrowid

            # 2️⃣ Process PDFs → get questions data
            questions_data = process_pdfs(paper_path, key_path)

            if not questions_data:
                flash("No questions found in the uploaded files!", "warning")
                return redirect(url_for('upload_paper'))

            # 3️⃣ Insert into questions
            for q in questions_data:
                if q['q_no'] is None:
                    continue  # Skip questions without valid question numbers

                cursor.execute("""
                    INSERT INTO questions (q_no, image_path, paper_id, subject_id, question_type, marks,
                                            negative_marks, correct_answers, range_min, range_max)
                    VALUES (%s, %s, %s, %s, %s, 1, 0.33, %s, %s, %s)
                """, (
                    q['q_no'],
                    q['image_path'],
                    paper_id,
                    subject_id,
                    q['question_type'],
                    json.dumps(q['correct_answers']
                               ) if q['correct_answers'] else None,
                    q.get('range_min'),
                    q.get('range_max')
                ))
            conn.commit()

            flash("Paper and questions saved successfully!", "success")

            # Clean up uploaded files (optional)
            try:
                os.remove(paper_path)
                os.remove(key_path)
            except:
                pass  # Ignore cleanup errors

        except Exception as e:
            conn.rollback()
            flash(f"Error processing files: {e}", "danger")
            # Clean up uploaded files on error
            try:
                os.remove(paper_path)
                os.remove(key_path)
            except:
                pass

        return redirect(url_for('upload_paper'))

    cursor.close()
    conn.close()
    return render_template('upload_paper.html', streams=streams)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# This is the missing part that was causing your issue!
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
