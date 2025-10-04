from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField, SubmitField, RadioField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
import sqlite3

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    role= RadioField("Role", choices=[("user", "User"), ("admin", "Admin")], validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = RadioField("Role", choices=[("user", "User"), ("admin", "Admin")], validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        conn = sqlite3.connect('job_applications.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username.data,))
        existing_user = cursor.fetchone()
        conn.close()
        if existing_user:
            raise ValidationError('Username already exists. Please choose a different one.')


class JobApplicationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    resume = FileField('Resume', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'doc', 'docx'], 'Only PDF and Word documents are allowed!')
    ])
    submit = SubmitField('Submit Application')

class JobPostingForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Job Description', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Add Job Posting')

class EditJobForm(FlaskForm):
    title = StringField('Job Title', validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField('Job Description', validators=[DataRequired(), Length(min=10, max=1000)])
    submit = SubmitField('Update Job Posting')

class ApplicationStatusForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('Pending', 'Pending'),
        ('Under Review', 'Under Review'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected')
    ], validators=[DataRequired()])
    submit = SubmitField('Update Status')
