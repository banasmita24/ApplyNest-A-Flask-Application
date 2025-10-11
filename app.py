from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf.csrf import CSRFProtect
import sqlite3
import os
from docx import Document
import fitz 
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegisterForm, JobApplicationForm, JobPostingForm, EditJobForm, ApplicationStatusForm, ResumeUploadForm
from werkzeug.utils import secure_filename
from nlp_utils import match_resume_to_jobs, update_schema_with_keywords
from resume_processor import ResumeProcessor

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('sqlite:///db.sqlite3')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.urandom(24)
UPLOAD_FOLDER = 'static/resumes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
update_schema_with_keywords()

# Theme support (light / dark)
THEME_OPTIONS = ('light', 'dark')

def get_theme():
    return session.get('theme', 'dark_professional')  # Default to dark

@app.context_processor
def inject_theme():
    # makes `current_theme` available in all templates, mapping dark_professional to dark
    theme = get_theme()
    if theme == 'dark_professional':
        current_theme = 'dark'
    else:
        current_theme = 'light'
    return dict(current_theme=current_theme)

@app.route('/set_theme/<theme>')
def set_theme(theme):
    if theme not in THEME_OPTIONS:
        theme = 'light'
    if theme == 'dark':
        session['theme'] = 'dark_professional'
    else:
        session['theme'] = theme
    return redirect(request.referrer or url_for('index'))

# Initialize CSRF protection
csrf = CSRFProtect(app)


# Database initialization
def connect_db():
    conn = sqlite3.connect('job_applications.db')
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def create_tables():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS job_postings (
                      id INTEGER PRIMARY KEY,
                      title TEXT,
                      description TEXT,
                      admin_id INTEGER,
                      FOREIGN KEY (admin_id) REFERENCES users (id) ON DELETE CASCADE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS job_applications (
                      id INTEGER PRIMARY KEY,
                      job_id INTEGER,
                      user_id INTEGER,
                      name TEXT,
                      email TEXT,
                      resume TEXT,
                      status TEXT DEFAULT 'Pending',
                      match_score REAL DEFAULT 0.0,
                      FOREIGN KEY (job_id) REFERENCES job_postings (id) ON DELETE CASCADE,
                      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY,
                      username TEXT UNIQUE,
                      password TEXT,
                      role TEXT)''')
    
    # Lightweight migrations for existing databases (SQLite-compatible)
    try:
        # job_applications table columns
        cursor.execute("PRAGMA table_info(job_applications)")
        job_app_cols = [column[1] for column in cursor.fetchall()]
        if 'match_score' not in job_app_cols:
            print("Adding match_score column to existing job_applications table...")
            cursor.execute("ALTER TABLE job_applications ADD COLUMN match_score REAL DEFAULT 0.0")
            print("✓ match_score column added")
        if 'status' not in job_app_cols:
            print("Adding status column to existing job_applications table...")
            cursor.execute("ALTER TABLE job_applications ADD COLUMN status TEXT DEFAULT 'Pending'")
            print("✓ status column added")

        # users table columns
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [col[1] for col in cursor.fetchall()]
        if 'full_name' not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
        if 'resume_path' not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN resume_path TEXT")
    except Exception as e:
        print(f"Migration error (this is normal for new databases): {e}")
    
    conn.commit()
    conn.close()

create_tables()


def migrate_existing_applications():
    """Calculate match scores for existing applications that don't have them"""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Find applications without match scores
        cursor.execute("SELECT ja.id, ja.job_id, ja.resume, jp.description FROM job_applications ja JOIN job_postings jp ON ja.job_id = jp.id WHERE ja.match_score = 0.0 OR ja.match_score IS NULL")
        applications = cursor.fetchall()
        
        if applications:
            print(f"Found {len(applications)} applications without match scores. Calculating...")
            processor = ResumeProcessor()
            updated_count = 0
            
            for app_id, job_id, resume_filename, job_description in applications:
                resume_path = os.path.join('static', 'resumes', resume_filename)
                if os.path.exists(resume_path):
                    match_score, status = processor.process_resume(resume_path, job_description)
                    if status == "Success":
                        cursor.execute("UPDATE job_applications SET match_score=? WHERE id=?", (match_score, app_id))
                        updated_count += 1
                        print(f"Updated application {app_id}: {match_score}% match")
            
            conn.commit()
            print(f"Successfully updated {updated_count} applications with match scores.")
        
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")


# Run migration for existing applications (commented out to prevent startup errors)
# migrate_existing_applications()


# Predefined admin user
def insert_admin_user():
    conn = connect_db()
    cursor = conn.cursor()
    # Hash the admin password before storing it
    hashed_password = generate_password_hash('admin123')
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                   ('admin', hashed_password, 'admin'))
    conn.commit()
    conn.close()

insert_admin_user()


@app.route('/')
def index():
    return render_template('index.html')


# Admin login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND role='admin'", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):  # Verify hashed password
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials for admin login, please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        full_name = form.full_name.data
        password = form.password.data
        role = form.role.data

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, full_name, password, role)
            VALUES (?, ?, ?, ?)
        """, (username, full_name, generate_password_hash(password), role))
        conn.commit()
        conn.close()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = form.role.data  # get selected role from form radio button

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND role=?", (username, role))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['full_name'] = user[5]  # index depends on table order; adjust
            session['role'] = user[3]

            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials, please try again.', 'error')
            return render_template('login.html', form=form)

    return render_template('login.html', form=form)

@app.before_request
def ensure_theme():
    # for quick testing force a visible dark theme if none selected
    if 'theme' not in session:
        session['theme'] = 'dark_professional'


@app.route('/user_dashboard')
def user_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = connect_db()
    cursor = conn.cursor()

    # Fetch full_name and resume_path
    cursor.execute("SELECT full_name, resume_path FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    full_name = row[0] if row else "User"
    resume_path = row[1] if row else None

    # Load resume text
    resume_text = ""
    resume_uploaded = bool(resume_path)
    if resume_uploaded and os.path.exists(resume_path):
        try:
            if resume_path.endswith('.pdf'):
                import fitz
                doc = fitz.open(resume_path)
                for page in doc:
                    resume_text += page.get_text()
            elif resume_path.endswith('.docx'):
                from docx import Document
                doc = Document(resume_path)
                for para in doc.paragraphs:
                    resume_text += para.text + "\n"
        except Exception as e:
            print(f"Error reading resume: {e}")

    # Fetch applied jobs
    cursor.execute('''SELECT jp.title, jp.description, ja.resume, ja.status
                      FROM job_applications ja
                      JOIN job_postings jp ON ja.job_id = jp.id
                      WHERE ja.user_id = ?''', (user_id,))
    applied_jobs = cursor.fetchall()

    # Fetch all job postings
    cursor.execute("SELECT * FROM job_postings")
    job_postings = cursor.fetchall()

    conn.close()

    matched_jobs = match_resume_to_jobs(resume_text) if resume_text else []
    resume_form = ResumeUploadForm()
    application_form = JobApplicationForm()

    return render_template('user_dashboard.html',
                           full_name=full_name,
                           job_postings=job_postings,
                           applied_jobs=applied_jobs,
                           matched_jobs=matched_jobs,
                           resume_uploaded=resume_uploaded,
                           resume_form=resume_form,
                           application_form=application_form)


@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    form = ResumeUploadForm()
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    if form.validate_on_submit():
        resume_file = form.resume_file.data
        filename = secure_filename(resume_file.filename)
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        resume_file.save(resume_path)

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET resume_path = ? WHERE username = ?", (resume_path, username))
        conn.commit()
        conn.close()

        flash('Resume uploaded successfully!', 'success')

    return redirect(url_for('user_dashboard'))


@app.route('/keywords/<int:job_id>')
def store_keywords(job_id):
    from nlp_utils import store_keywords_for_job
    store_keywords_for_job(job_id)
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/<int:job_id>', methods=['POST'])
def admin(job_id):
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('login'))

    form = JobApplicationForm()
    if form.validate_on_submit():
        user_id = session['user_id']
        email = form.email.data
        resume = form.resume.data

        # Fetch full_name from database
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT full_name FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        full_name = row[0] if row else "Unknown"
        
        # Save resume with safe filename and original extension
        file_extension = os.path.splitext(resume.filename)[1] or '.pdf'
        safe_name = "_".join(full_name.split())
        resume_filename = f"{safe_name}_{email}{file_extension}"
        resume_path = os.path.join('static', 'resumes', resume_filename)
        os.makedirs(os.path.join('static', 'resumes'), exist_ok=True)
        resume.save(resume_path)

        # Get job description for match scoring
        cursor.execute("SELECT description FROM job_postings WHERE id=?", (job_id,))
        job_posting = cursor.fetchone()
        
        if not job_posting:
            conn.close()
            flash('Job posting not found.', 'error')
            return redirect(url_for('user_dashboard'))
        
        job_description = job_posting[0]
        
        # Calculate match score
        processor = ResumeProcessor()
        match_score, status = processor.process_resume(resume_path, job_description)
        
        if status != "Success":
            flash(f'Warning: {status}. Application submitted without match score.', 'warning')
            match_score = 0.0

        # Insert application with match score
        cursor.execute("INSERT INTO job_applications (job_id, user_id, name, email, resume, status, match_score) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (job_id, user_id, full_name, email, resume_filename, 'Pending', match_score))
        conn.commit()
        conn.close()
        
        if match_score > 0:
            flash(f'Application submitted successfully! Match score: {match_score}%', 'success')
        else:
            flash('Application submitted successfully!', 'success')
        return redirect(url_for('user_dashboard'))
    else:
        flash('Please correct the errors in your application.', 'error')
        return redirect(url_for('user_dashboard'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    # Fetch only job postings created by the currently logged-in admin
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings WHERE admin_id=?", (session['user_id'],))
    job_postings = cursor.fetchall()
    conn.close()
    
    form = JobPostingForm()
    edit_form = EditJobForm()
    status_form = ApplicationStatusForm()
    return render_template('admin_dashboard.html', 
                         job_postings=job_postings, 
                         job_applications=[],  # Empty list when no applications
                         form=form, 
                         edit_form=edit_form, 
                         status_form=status_form,
                         current_sort='match_score',
                         current_order='desc')




@app.route('/view_applications')
def view_applications():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    admin_id = session['user_id']
    sort_by = request.args.get('sort', 'match_score')  # Default sort by match score
    sort_order = request.args.get('order', 'desc')  # Default descending order
    
    conn = connect_db()
    cursor = conn.cursor()

    # Validate sort parameters
    valid_sort_fields = ['match_score', 'name', 'email', 'status', 'job_title']
    if sort_by not in valid_sort_fields:
        sort_by = 'match_score'
    
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'

    # Build ORDER BY clause
    order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
    if sort_by == 'job_title':
        order_clause = "ORDER BY jp.title " + sort_order.upper()

    cursor.execute(f"""
        SELECT ja.id, ja.name, ja.email, ja.resume, jp.title, ja.status, ja.match_score
        FROM job_applications ja
        JOIN job_postings jp ON ja.job_id = jp.id
        WHERE jp.admin_id = ?
        {order_clause}
    """, (admin_id,))

    job_applications = cursor.fetchall()

    # Get job postings for the admin (needed for the template)
    cursor.execute("SELECT * FROM job_postings WHERE admin_id=?", (admin_id,))
    job_postings = cursor.fetchall()
    conn.close()

    applications = [{
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'resume': row[3],
        'job_title': row[4],
        'status': row[5],
        'match_score': row[6] if row[6] is not None else 0.0
    } for row in job_applications]
    
    form = JobPostingForm()
    edit_form = EditJobForm()
    status_form = ApplicationStatusForm()
    
    return render_template('admin_dashboard.html', 
                         job_postings=job_postings,
                         job_applications=applications, 
                         form=form,
                         edit_form=edit_form,
                         status_form=status_form,
                         current_sort=sort_by,
                         current_order=sort_order)

@app.route('/update_status/<int:application_id>',methods =['POST'])
def update_status(application_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    form = ApplicationStatusForm()
    if form.validate_on_submit():
        new_status = form.status.data
        conn= connect_db()
        cursor =conn.cursor()
        cursor.execute("UPDATE job_applications SET status=? WHERE id=?", (new_status,application_id))
        conn.commit()
        conn.close()

        flash(f'Application status updated to "{new_status}" successfully')
        return redirect(url_for('view_applications'))
    else:
        flash('Please correct the errors in your status update.', 'error')
        return redirect(url_for('view_applications'))



@app.route('/add_job', methods=['POST'])
def add_job():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    form = JobPostingForm()
    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        admin_id = session['user_id']  # Get the ID of the currently logged-in admin

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO job_postings (title, description, admin_id) VALUES (?, ?, ?)",
                       (title, description, admin_id))
        conn.commit()
        conn.close()
        flash('Job posting added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Please correct the errors in your job posting.', 'error')
        return redirect(url_for('admin_dashboard'))


@app.route('/edit_job/<int:job_id>', methods=['POST', 'GET'])
def edit_job(job_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    # Check if the job posting being edited belongs to the currently logged-in admin
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings WHERE id=? AND admin_id=?", (job_id, session['user_id']))
    job_posting = cursor.fetchone()
    conn.close()
    
    if not job_posting:
        flash("You don't have permission to edit this job posting.", 'error')
        return redirect(url_for('admin_dashboard'))
    
    form = EditJobForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        title = form.title.data
        description = form.description.data

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE job_postings SET title=?, description=? WHERE id=?", (title, description, job_id))
        conn.commit()
        conn.close()
        flash('Job posting updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    elif request.method == 'POST':
        flash('Please correct the errors in your job posting.', 'error')
        return render_template('edit_job.html', form=form, job_id=job_id, current_job=job_posting)
    else:
        # GET request - show the edit form
        return render_template('edit_job.html', form=form, job_id=job_id, current_job=job_posting)


@app.route('/migrate_scores')
def migrate_scores():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    try:
        migrate_existing_applications()
        flash('Migration completed successfully! All existing applications now have match scores.', 'success')
    except Exception as e:
        flash(f'Migration failed: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))


@app.route('/recalculate_scores/<int:job_id>')
def recalculate_scores(job_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    # Check if the job posting belongs to the currently logged-in admin
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings WHERE id=? AND admin_id=?", (job_id, session['user_id']))
    job_posting = cursor.fetchone()
    
    if not job_posting:
        flash("You don't have permission to recalculate scores for this job posting.", 'error')
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    job_description = job_posting[2]  # description is at index 2
    
    # Get all applications for this job
    cursor.execute("SELECT id, resume FROM job_applications WHERE job_id=?", (job_id,))
    applications = cursor.fetchall()
    
    processor = ResumeProcessor()
    updated_count = 0
    
    for app_id, resume_filename in applications:
        resume_path = os.path.join('static', 'resumes', resume_filename)
        if os.path.exists(resume_path):
            match_score, status = processor.process_resume(resume_path, job_description)
            if status == "Success":
                cursor.execute("UPDATE job_applications SET match_score=? WHERE id=?", (match_score, app_id))
                updated_count += 1
    
    conn.commit()
    conn.close()
    
    flash(f'Successfully recalculated match scores for {updated_count} applications!', 'success')
    return redirect(url_for('view_applications'))


@app.route('/delete_job/<int:job_id>')
def delete_job(job_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    # Check if the job posting being deleted belongs to the currently logged-in admin
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings WHERE id=? AND admin_id=?", (job_id, session['user_id']))
    job_posting = cursor.fetchone()
    conn.close()
    if not job_posting:
        flash("You don't have permission to delete this job posting.", 'error')
        return redirect(url_for('admin_dashboard'))

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_postings WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    flash('Job posting deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
