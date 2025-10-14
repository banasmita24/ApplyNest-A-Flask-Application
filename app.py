from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegisterForm, JobApplicationForm, JobPostingForm, EditJobForm, ApplicationStatusForm

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('sqlite:///db.sqlite3')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.urandom(24)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


# User model class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username, password_hash, role):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def get_id(self):
        return str(self.id)

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False


# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None


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
                      FOREIGN KEY (job_id) REFERENCES job_postings (id) ON DELETE CASCADE,
                      FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY,
                      username TEXT UNIQUE,
                      password TEXT,
                      role TEXT)''')
    conn.commit()
    conn.close()

create_tables()


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
            user_obj = User(user[0], user[1], user[2], user[3])
            login_user(user_obj)
            flash('Successfully logged in as admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials for admin login, please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = 'admin' if form.is_admin.data else 'user'

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, generate_password_hash(password), role))
        conn.commit()
        conn.close()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND role='user'", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):  # Verify hashed password
            user_obj = User(user[0], user[1], user[2], user[3])
            login_user(user_obj)
            flash('Successfully logged in!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials for user login, please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html', form=form)


@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        flash('Access denied. Admin users cannot access user dashboard.', 'error')
        return redirect(url_for('admin_dashboard'))

    user_id = current_user.id
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings")
    job_postings = cursor.fetchall()

    # Fetch the jobs the user has applied for based on user_id
    cursor.execute("""
        SELECT jp.title, jp.description, ja.resume, ja.status
        FROM job_applications ja
        JOIN job_postings jp ON ja.job_id = jp.id
        WHERE ja.user_id = ?
    """, (current_user.id,))
    applied_jobs = cursor.fetchall()

    conn.close()
    form = JobApplicationForm()
    return render_template('user_dashboard.html', job_postings=job_postings, applied_jobs=applied_jobs, form=form)


@app.route('/apply/<int:job_id>', methods=['POST'])
@login_required
def apply(job_id):
    if current_user.role != 'user':
        flash('Access denied. Admin users cannot apply for jobs.', 'error')
        return redirect(url_for('admin_dashboard'))

    form = JobApplicationForm()
    if form.validate_on_submit():
        user_id = current_user.id
        name = form.name.data
        email = form.email.data
        resume = form.resume.data

        resume_filename = f"{name}_{email}.pdf"
        resume_path = os.path.join('static', 'resumes', resume_filename)

        if not os.path.exists(os.path.join('static', 'resumes')):
            os.makedirs(os.path.join('static', 'resumes'))

        resume.save(resume_path)

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO job_applications (job_id, user_id, name, email, resume, status) VALUES (?, ?, ?, ?, ?, ?)",
                       (job_id, user_id, name, email, resume_filename, 'Pending'))  # Save user_id with the application
        conn.commit()
        conn.close()
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('user_dashboard'))
    else:
        flash('Please correct the errors in your application.', 'error')
        return redirect(url_for('user_dashboard'))


@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied. User accounts cannot access admin dashboard.', 'error')
        return redirect(url_for('user_dashboard'))
    # Fetch only job postings created by the currently logged-in admin
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings WHERE admin_id=?", (current_user.id,))
    job_postings = cursor.fetchall()
    conn.close()
    
    form = JobPostingForm()
    edit_form = EditJobForm()
    status_form = ApplicationStatusForm()
    return render_template('admin_dashboard.html', job_postings=job_postings, form=form, edit_form=edit_form, status_form=status_form)


@app.route('/view_applications')
@login_required
def view_applications():
    if current_user.role != 'admin':
        flash('Access denied. Only admin users can view applications.', 'error')
        return redirect(url_for('user_dashboard'))

    admin_id = current_user.id
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ja.id, ja.name, ja.email, ja.resume, jp.title ,ja.status
        FROM job_applications ja
        JOIN job_postings jp ON ja.job_id = jp.id
        WHERE jp.admin_id = ?
    """, (admin_id,))

    job_applications = cursor.fetchall()
    conn.close()

    applications = [{
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'resume': row[3],
        'job_title': row[4],
        'status':row[5]
    } for row in job_applications]

    status_form = ApplicationStatusForm()
    return render_template('admin_dashboard.html', job_applications=applications, status_form=status_form)

@app.route('/update_status/<int:application_id>',methods =['POST'])
@login_required
def update_status(application_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admin users can update application status.', 'error')
        return redirect(url_for('user_dashboard'))
    
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
@login_required
def add_job():
    if current_user.role != 'admin':
        flash('Access denied. Only admin users can add job postings.', 'error')
        return redirect(url_for('user_dashboard'))
    
    form = JobPostingForm()
    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        admin_id = current_user.id  # Get the ID of the currently logged-in admin

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
@login_required
def edit_job(job_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admin users can edit job postings.', 'error')
        return redirect(url_for('user_dashboard'))
    
    form = EditJobForm()
    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data

        # Check if the job posting being edited belongs to the currently logged-in admin
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_postings WHERE id=? AND admin_id=?", (job_id, current_user.id))
        job_posting = cursor.fetchone()
        conn.close()
        if not job_posting:
            flash("You don't have permission to edit this job posting.", 'error')
            return redirect(url_for('admin_dashboard'))

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE job_postings SET title=?, description=? WHERE id=?", (title, description, job_id))
        conn.commit()
        conn.close()
        flash('Job posting updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Please correct the errors in your job posting.', 'error')
        return redirect(url_for('admin_dashboard'))


@app.route('/delete_job/<int:job_id>')
@login_required
def delete_job(job_id):
    if current_user.role != 'admin':
        flash('Access denied. Only admin users can delete job postings.', 'error')
        return redirect(url_for('user_dashboard'))
    # Check if the job posting being deleted belongs to the currently logged-in admin
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_postings WHERE id=? AND admin_id=?", (job_id, current_user.id))
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
