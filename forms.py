from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, BooleanField, DateTimeField, RadioField, HiddenField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from datetime import datetime
from models import User, Module
from wtforms.validators import DataRequired, NumberRange
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('I am a', choices=[('student', 'Student')])  # Only students can self-register
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one or log in.')

class ModuleForm(FlaskForm):
    code = StringField('Module Code', validators=[DataRequired(), Length(max=10)])
    name = StringField('Module Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Create Module')
    
    def validate_code(self, code):
        module = Module.query.filter_by(code=code.data.upper()).first()
        if module:
            raise ValidationError('Module code already exists. Please use a different code.')
            
class TakeModuleForm(FlaskForm):
    module_id = SelectField('Select Existing Module', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Take Module')

class EnrollmentForm(FlaskForm):
    modules = SelectMultipleField('Select Modules', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save Enrollment')
    
class AdminCreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Role', choices=[('student', 'Student'), ('lecturer', 'Lecturer')])
    submit = SubmitField('Create User')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')
            
class AdminEditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('student', 'Student'), ('lecturer', 'Lecturer')])
    reset_password = BooleanField('Reset Password')
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Save Changes')
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(AdminEditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
        
    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

class CreateTestForm(FlaskForm):
    title = StringField('Test Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    module_id = SelectField('Module', coerce=int, validators=[DataRequired()])
    time_limit_minutes = IntegerField('Time Limit (minutes)', validators=[DataRequired()])
    due_date = DateTimeField('Due Date (optional)', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    max_attempts = IntegerField('Maximum Attempts', validators=[DataRequired()])
    passing_score = IntegerField('Passing Score (%)', validators=[DataRequired()])
    submit = SubmitField('Create Test')

class QuestionForm(FlaskForm):
    text = TextAreaField('Question Text', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('short_answer', 'Short Answer')
    ], validators=[DataRequired()])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Question')

class OptionForm(FlaskForm):
    text = StringField('Option Text', validators=[DataRequired()])
    is_correct = BooleanField('Correct Answer')

class AnswerForm(FlaskForm):
    selected_option = RadioField('Choose Answer', coerce=int)
    question_id = HiddenField('Question ID')
    
class AdminCreateModuleForm(FlaskForm):
    code = StringField('Module Code', validators=[DataRequired(), Length(max=10)])
    name = StringField('Module Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    lecturer_id = SelectField('Assign to Lecturer', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Module')
    
    def validate_code(self, code):
        module = Module.query.filter_by(code=code.data).first()
        if module:
            raise ValidationError('That module code is already in use. Please choose a different one.')
            
class AdminDashboardFilterForm(FlaskForm):
    user_type = SelectField('Filter by User Type', choices=[
        ('all', 'All Users'),
        ('student', 'Students Only'),
        ('lecturer', 'Lecturers Only'),
        ('admin', 'Admins Only')
    ], default='all')
    search = StringField('Search by Name or Email')
    submit = SubmitField('Apply Filters')
