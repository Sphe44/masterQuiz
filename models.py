from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Association table for the many-to-many relationship between Student and Module
student_module = db.Table('student_module',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('module_id', db.Integer, db.ForeignKey('module.id'), primary_key=True)
)

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # e.g., CSC101
    name = db.Column(db.String(100), nullable=False)  # e.g., "Introduction to Computer Science"
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key for the lecturer who teaches this module
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationship with tests created for this module
    tests = db.relationship('Test', backref='module', lazy=True)
    
    def __repr__(self):
        return f"<Module {self.code}: {self.name}>"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'lecturer', or 'admin'
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    face_encodings = db.Column(db.Text, nullable=True)  # store face encoding data as JSON
    
    # Relationships
    created_tests = db.relationship('Test', backref='author', lazy=True, 
                                   foreign_keys='Test.lecturer_id')
    test_attempts = db.relationship('TestAttempt', backref='student', lazy=True)
    
    # Relationship for lecturers and the modules they teach
    taught_modules = db.relationship('Module', backref='lecturer', lazy=True)
    
    # Relationship for students and the modules they're enrolled in
    enrolled_modules = db.relationship('Module', 
                                      secondary=student_module,
                                      backref=db.backref('enrolled_students', lazy='dynamic'),
                                      lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        if not self.password_hash:
            print(f"ERROR: User {self.username} has no password hash!")
            return False
        try:
            result = check_password_hash(self.password_hash, password)
            print(f"Password check for {self.username}: {'Success' if result else 'Failed'}")
            return result
        except Exception as e:
            print(f"ERROR checking password for {self.username}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def is_lecturer(self):
        return self.role == 'lecturer'
    
    def is_student(self):
        return self.role == 'student'
        
    def is_admin(self):
        print(f"Checking if user {self.username} is admin. Role: {self.role}")
        result = self.role == 'admin'
        print(f"is_admin result: {result}")
        return result
        
    def enroll_in_module(self, module):
        if not self.is_enrolled_in(module):
            self.enrolled_modules.append(module)
            return True
        return False
    
    def unenroll_from_module(self, module):
        if self.is_enrolled_in(module):
            self.enrolled_modules.remove(module)
            return True
        return False
    
    def is_enrolled_in(self, module):
        return self.enrolled_modules.filter(student_module.c.module_id == module.id).count() > 0

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    time_limit_minutes = db.Column(db.Integer, nullable=False, default=60)
    due_date = db.Column(db.DateTime, nullable=True)
    max_attempts = db.Column(db.Integer, nullable=False, default=1)
    passing_score = db.Column(db.Integer, nullable=False, default=60)  # Percentage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Foreign keys
    lecturer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    
    # Relationships
    questions = db.relationship('Question', backref='test', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('TestAttempt', backref='test', lazy=True, cascade='all, delete-orphan')
    
    def get_total_points(self):
        return sum(q.points for q in self.questions)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'multiple_choice', 'short_answer', etc.
    points = db.Column(db.Integer, nullable=False, default=1)
    
    # Foreign keys
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    
    # Relationships
    options = db.relationship('QuestionOption', backref='question', lazy=True, cascade='all, delete-orphan')
    answers = db.relationship('StudentAnswer', backref='question', lazy=True)

class QuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)

class TestAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    answers = db.relationship('StudentAnswer', backref='attempt', lazy=True, cascade='all, delete-orphan')
    face_logs = db.relationship('FaceDetectionLog', backref='attempt', lazy=True, cascade='all, delete-orphan')

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submitted_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    attempt_id = db.Column(db.Integer, db.ForeignKey('test_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('question_option.id'), nullable=True)
    
    # For non-multiple choice questions
    text_answer = db.Column(db.Text, nullable=True)
    
    # Points earned for this answer
    points_earned = db.Column(db.Float, nullable=True)
    
    # Add relationship with QuestionOption
    selected_option = db.relationship('QuestionOption', foreign_keys=[selected_option_id])

class FaceDetectionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)  # 'face_detected', 'no_face', 'multiple_faces', etc.
    details = db.Column(db.Text, nullable=True)  # Additional details if needed
    
    # Foreign keys
    attempt_id = db.Column(db.Integer, db.ForeignKey('test_attempt.id'), nullable=False)
