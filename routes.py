from flask import render_template, url_for, flash, redirect, request, jsonify, abort
from flask_login import login_user, current_user, logout_user, login_required
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import json
from datetime import datetime
from werkzeug.exceptions import InternalServerError
import re
from app import app, db
from models import User, Test, Question, QuestionOption, TestAttempt, StudentAnswer, FaceDetectionLog, Module
from forms import (LoginForm, RegistrationForm, CreateTestForm, QuestionForm, 
                  ModuleForm, EnrollmentForm, TakeModuleForm, AdminCreateUserForm, 
                  AdminEditUserForm, AdminCreateModuleForm, AdminDashboardFilterForm)

# Authentication routes
@app.route('/')
def index():
    return render_template('index.html', title='Home')

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Login route accessed")
    
    if current_user.is_authenticated:
        print(f"User already authenticated as: {current_user.username}, role: {current_user.role}")
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_lecturer():
            return redirect(url_for('lecturer_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        print(f"Form submitted with email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            print(f"User found: {user.username}, role: {user.role}")
            password_check = user.check_password(form.password.data)
            print(f"Password check result: {password_check}")
            
            if password_check:
                login_user(user)
                print(f"User logged in successfully")
                next_page = request.args.get('next')
                
                if user.is_admin():
                    print("Redirecting to admin dashboard")
                    return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
                elif user.is_lecturer():
                    return redirect(next_page) if next_page else redirect(url_for('lecturer_dashboard'))
                else:
                    return redirect(next_page) if next_page else redirect(url_for('student_dashboard'))
        else:
            print(f"No user found with email: {form.email.data}")
            
        flash('Login unsuccessful. Please check email and password.', 'danger')
    
    return render_template('login.html', title='Login', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# API route for JWT token generation
@app.route('/api/token', methods=['POST'])
def get_token():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400
    
    email = request.json.get('email', None)
    password = request.json.get('password', None)
    
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Bad username or password"}), 401
    
    access_token = create_access_token(identity=str(user.id))
    print(f"API DEBUG - Login: Created token for user ID: {user.id}")
    return jsonify(access_token=access_token, user_id=user.id, role=user.role)

# Student routes
@app.route('/student/available-tests')
@login_required
def available_tests():
    if not current_user.is_student():
        flash('Access denied: You need to be a student to view available tests.', 'danger')
        return redirect(url_for('index'))
    
    # Get the student's enrolled modules
    enrolled_modules = current_user.enrolled_modules.all()
    
    # Get available tests from enrolled modules
    available_tests = []
    if enrolled_modules:
        module_ids = [module.id for module in enrolled_modules]
        available_tests = Test.query.filter(
            Test.module_id.in_(module_ids),
            ((Test.due_date >= datetime.utcnow()) | (Test.due_date == None)),
            Test.is_active == True
        ).order_by(Test.due_date.asc()).all()

    return render_template(
        'student/available_tests.html',
        title='Available Tests',
        available_tests=available_tests,
        enrolled_modules=enrolled_modules
    )

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if not current_user.is_student():
        flash('Access denied: You need to be a student to view this page.', 'danger')
        return redirect(url_for('index'))
    
    # Get the student's enrolled modules
    enrolled_modules = current_user.enrolled_modules.all()
    
    # Get available tests from enrolled modules (that haven't passed due date)
    available_tests = []
    if enrolled_modules:
        module_ids = [module.id for module in enrolled_modules]
        
        # Apply the due date and active filters
        available_tests = Test.query.filter(
            Test.module_id.in_(module_ids),
            ((Test.due_date >= datetime.utcnow()) | (Test.due_date == None)),
            Test.is_active == True
        ).all()
    
    # Get completed tests
    completed_attempts = TestAttempt.query.filter_by(
        student_id=current_user.id,
        is_completed=True
    ).order_by(TestAttempt.end_time.desc()).all()
    
    # For dashboard template, rename available_tests to upcoming_tests
    return render_template(
        'student/dashboard.html',
        title='Student Dashboard',
        upcoming_tests=available_tests,  # Match template variable name
        completed_tests=completed_attempts,  # Match template variable name  
        enrolled_modules=enrolled_modules
    )

@app.route('/student/test/<int:test_id>')
@login_required
def start_test(test_id):
    if not current_user.is_student():
        flash('Access denied: You need to be a student to take a test.', 'danger')
        return redirect(url_for('index'))
    
    test = Test.query.get_or_404(test_id)
    
    # Check if the student is enrolled in the module this test belongs to
    module = Module.query.get(test.module_id)
    if not current_user.is_enrolled_in(module):
        flash('You must be enrolled in this course to take this test.', 'warning')
        return redirect(url_for('manage_enrollment'))
    
    # Check if test is still available
    if test.due_date and test.due_date < datetime.utcnow():
        flash('This test is no longer available.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Check if the student has exceeded max attempts
    attempts_count = TestAttempt.query.filter_by(
        test_id=test.id,
        student_id=current_user.id
    ).count()
    
    if attempts_count >= test.max_attempts:
        flash(f'You have already used all {test.max_attempts} attempt(s) for this test.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Create a new test attempt
    attempt = TestAttempt(
        test_id=test.id,
        student_id=current_user.id,
        start_time=datetime.utcnow()
    )
    db.session.add(attempt)
    db.session.commit()
    
    # Generate a JWT token for API access during the test
    access_token = create_access_token(identity=str(current_user.id))
    print(f"API DEBUG - Start test: Created token for user ID: {current_user.id}")
    
    # Redirect to the test-taking page with the token
    return redirect(url_for('take_test', attempt_id=attempt.id, token=access_token))

@app.route('/student/take-test/<int:attempt_id>')
@login_required
def take_test(attempt_id):
    if not current_user.is_student():
        flash('Access denied: You need to be a student to take a test.', 'danger')
        return redirect(url_for('index'))
    
    attempt = TestAttempt.query.get_or_404(attempt_id)
    
    # Security check - ensure this attempt belongs to the current user
    if attempt.student_id != current_user.id:
        abort(403)
    
    # Check if attempt is already completed
    if attempt.is_completed:
        flash('This test has already been completed.', 'info')
        return redirect(url_for('view_test_results', attempt_id=attempt.id))
    
    test = Test.query.get(attempt.test_id)
    questions = Question.query.filter_by(test_id=test.id).all()
    
    # Calculate remaining time
    elapsed_seconds = (datetime.utcnow() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, (test.time_limit_minutes * 60) - elapsed_seconds)
    
    # Get token from query param or create a new one
    token = request.args.get('token') or create_access_token(identity=str(current_user.id))
    print(f"API DEBUG - Created token for user ID: {current_user.id}, Token: {token}")
    
    return render_template(
        'student/take_test.html',
        title=f'Take Test: {test.title}',
        test=test,
        attempt=attempt,
        questions=questions,
        remaining_seconds=remaining_seconds,
        token=token
    )

@app.route('/api/submit-answer', methods=['POST'])
@jwt_required()
def submit_answer():
    try:
        # Convert string user_id to int (JWT stores strings)
        user_id = int(get_jwt_identity())
        
        print(f"API DEBUG - submit_answer: user_id={user_id}")
        
        data = request.json
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        selected_option_id = data.get('selected_option_id')
        
        print(f"API DEBUG - submit_answer: attempt_id={attempt_id}, question_id={question_id}, option_id={selected_option_id}")
        
        # Verify user owns the attempt
        attempt = TestAttempt.query.get_or_404(attempt_id)
        print(f"API DEBUG - Found attempt, student_id={attempt.student_id}")
        
        if attempt.student_id != user_id:
            print(f"API DEBUG - Unauthorized: attempt.student_id={attempt.student_id} != user_id={user_id}")
            return jsonify({"error": "Unauthorized", "message": "User does not own this attempt"}), 403
    
        # Check if already answered
        existing_answer = StudentAnswer.query.filter_by(
            attempt_id=attempt_id,
            question_id=question_id
        ).first()
        
        print(f"API DEBUG - Existing answer found: {existing_answer is not None}")
        
        if existing_answer:
            # Update existing answer
            existing_answer.selected_option_id = selected_option_id
            existing_answer.submitted_time = datetime.utcnow()
            print(f"API DEBUG - Updated existing answer")
        else:
            # Create new answer
            question = Question.query.get(question_id)
            if not question:
                print(f"API DEBUG - Question not found: {question_id}")
                return jsonify({"error": "Question not found"}), 404
                
            print(f"API DEBUG - Creating new answer")
            answer = StudentAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option_id=selected_option_id
            )
            
            # Auto-grade multiple choice
            if question.question_type == 'multiple_choice' and selected_option_id:
                option = QuestionOption.query.get(selected_option_id)
                answer.points_earned = question.points if option and option.is_correct else 0
            
            db.session.add(answer)
        
        db.session.commit()
        print(f"API DEBUG - Answer saved successfully!")
        return jsonify({"success": True})
    
    except Exception as e:
        print(f"API DEBUG - ERROR in submit_answer: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit-test', methods=['POST'])
@jwt_required()
def submit_test():
    try:
        # Convert string user_id to int (JWT stores strings)
        user_id = int(get_jwt_identity())
        
        print(f"API DEBUG - submit_test: user_id={user_id}")
        
        data = request.json
        attempt_id = data.get('attempt_id')
        
        print(f"API DEBUG - submit_test: attempt_id={attempt_id}")
        
        # Verify user owns the attempt
        attempt = TestAttempt.query.get_or_404(attempt_id)
        print(f"API DEBUG - Found attempt, student_id={attempt.student_id}")
        
        if attempt.student_id != user_id:
            print(f"API DEBUG - Unauthorized: attempt.student_id={attempt.student_id} != user_id={user_id}")
            return jsonify({"error": "Unauthorized", "message": "User does not own this attempt"}), 403
        
        # Mark test as completed
        attempt.is_completed = True
        attempt.end_time = datetime.utcnow()
        
        # Calculate total score
        test = Test.query.get(attempt.test_id)
        total_possible = test.get_total_points()
        
        print(f"API DEBUG - Test total points: {total_possible}")
        
        if total_possible > 0:
            total_earned = sum(answer.points_earned or 0 for answer in attempt.answers)
            attempt.score = (total_earned / total_possible) * 100
            print(f"API DEBUG - Total earned: {total_earned}, Score: {attempt.score}")
        else:
            attempt.score = 0
            print(f"API DEBUG - No points possible, score set to 0")
        
        db.session.commit()
        print(f"API DEBUG - Test submitted successfully!")
        
        return jsonify({
            "success": True, 
            "score": attempt.score,
            "result_url": url_for('view_test_results', attempt_id=attempt.id)
        })
    
    except Exception as e:
        print(f"API DEBUG - ERROR in submit_test: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/face-log', methods=['POST'])
@jwt_required()
def log_face_detection():
    try:
        # Convert string user_id to int (JWT stores strings)
        user_id = int(get_jwt_identity())
        
        print(f"API DEBUG - log_face_detection: user_id={user_id}")
        
        data = request.json
        attempt_id = data.get('attempt_id')
        status = data.get('status')
        details = data.get('details', '')
        
        print(f"API DEBUG - log_face_detection: attempt_id={attempt_id}, status={status}")
        
        # Verify user owns the attempt
        attempt = TestAttempt.query.get_or_404(attempt_id)
        print(f"API DEBUG - Found attempt, student_id={attempt.student_id}")
        
        if attempt.student_id != user_id:
            print(f"API DEBUG - Unauthorized: attempt.student_id={attempt.student_id} != user_id={user_id}")
            return jsonify({"error": "Unauthorized", "message": "User does not own this attempt"}), 403
        
        # Create log entry
        log = FaceDetectionLog(
            attempt_id=attempt_id,
            status=status,
            details=details
        )
        db.session.add(log)
        db.session.commit()
        print(f"API DEBUG - Face log saved successfully!")
        
        return jsonify({"success": True})
    
    except Exception as e:
        print(f"API DEBUG - ERROR in log_face_detection: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/student/results/<int:attempt_id>')
@login_required
def view_test_results(attempt_id):
    if not current_user.is_student():
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    attempt = TestAttempt.query.get_or_404(attempt_id)
    
    # Security check - ensure this attempt belongs to the current user
    if attempt.student_id != current_user.id:
        abort(403)
    
    test = Test.query.get(attempt.test_id)
    questions = Question.query.filter_by(test_id=test.id).all()
    
    # Collect answers for each question
    question_answers = {}
    for question in questions:
        answer = StudentAnswer.query.filter_by(
            attempt_id=attempt.id,
            question_id=question.id
        ).first()
        question_answers[question.id] = answer
    
    return render_template(
        'student/test_results.html',
        title='Test Results',
        test=test,
        attempt=attempt,
        questions=questions,
        answers=question_answers,
        passed=(attempt.score >= test.passing_score if attempt.score else False)
    )

# Module routes for lecturers
@app.route('/lecturer/modules')
@login_required
def manage_modules():
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to manage modules.', 'danger')
        return redirect(url_for('index'))
    
    modules = Module.query.filter_by(lecturer_id=current_user.id).order_by(Module.code).all()
    
    # Get modules available to take (assigned to other lecturers or unassigned)
    available_modules = Module.query.filter(
        (Module.lecturer_id != current_user.id) | 
        (Module.lecturer_id == None)
    ).order_by(Module.code).all()
    
    return render_template(
        'lecturer/manage_modules.html',
        title='Manage Modules',
        modules=modules,
        available_modules=available_modules
    )
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    try:
        if request.method == 'POST':
            # Update the user's email
            email = request.form['email']

            # Validate email format
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash('Invalid email address. Please enter a valid email.', 'danger')
                return render_template('edit_profile.html', user=current_user)
            
            if email != current_user.email:
                current_user.email = email

            # Update the password if provided
            password = request.form['password']
            if password:
                current_user.set_password(password)  # Update password using set_password method

            # Commit the changes to the database
            db.session.commit()

            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('profile'))  # Redirect to the profile page

        return render_template('edit_profile.html', user=current_user)
    
    except Exception as e:
        db.session.rollback()  # Rollback any changes if there's an error
        flash(f'An error occurred while updating your profile: {str(e)}', 'danger')
        return render_template('edit_profile.html', user=current_user)
@app.route('/lecturer/modules/create', methods=['GET', 'POST'])
@login_required
def create_module():
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to create modules.', 'danger')
        return redirect(url_for('index'))
    
    # Get all available modules not yet assigned to this lecturer
    available_modules = Module.query.filter(
        (Module.lecturer_id != current_user.id) | 
        (Module.lecturer_id == None)
    ).order_by(Module.code).all()
    
    form = ModuleForm()
    if form.validate_on_submit():
        module = Module(
            code=form.code.data.upper(),
            name=form.name.data,
            description=form.description.data,
            lecturer_id=current_user.id
        )
        db.session.add(module)
        db.session.commit()
        
        flash(f'Module "{module.code}: {module.name}" created successfully!', 'success')
        return redirect(url_for('manage_modules'))
    
    return render_template(
        'lecturer/create_module.html',
        title='Create Module',
        form=form,
        available_modules=available_modules
    )

@app.route('/lecturer/modules/take/<int:module_id>')
@login_required
def take_module(module_id):
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to take modules.', 'danger')
        return redirect(url_for('index'))
    
    # Get the module
    module = Module.query.get_or_404(module_id)
    
    # Check if the module is available (not already assigned to this lecturer)
    if module.lecturer_id == current_user.id:
        flash('You are already teaching this module.', 'info')
        return redirect(url_for('manage_modules'))
    
    # Assign the module to this lecturer
    module.lecturer_id = current_user.id
    db.session.commit()
    
    flash(f'You are now teaching module "{module.code}: {module.name}"', 'success')
    return redirect(url_for('manage_modules'))

@app.route('/lecturer/modules/<int:module_id>')
@login_required
def module_details(module_id):
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to view module details.', 'danger')
        return redirect(url_for('index'))
    
    module = Module.query.get_or_404(module_id)
    
    # Security check - ensure this module belongs to the current lecturer
    if module.lecturer_id != current_user.id:
        abort(403)
    
    return render_template(
        'lecturer/module_details.html',
        title=f'Module: {module.code}',
        module=module
    )

@app.route('/lecturer/modules/<int:module_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_module(module_id):
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to edit modules.', 'danger')
        return redirect(url_for('index'))
    
    module = Module.query.get_or_404(module_id)
    
    # Security check - ensure this module belongs to the current lecturer
    if module.lecturer_id != current_user.id:
        abort(403)
    
    form = ModuleForm()
    if request.method == 'GET':
        form.code.data = module.code
        form.name.data = module.name
        form.description.data = module.description
    
    if form.validate_on_submit():
        # Skip validation for the current module code
        if form.code.data.upper() != module.code:
            existing_module = Module.query.filter_by(code=form.code.data.upper()).first()
            if existing_module:
                form.code.errors.append('Module code already exists. Please use a different code.')
                return render_template(
                    'lecturer/create_module.html',
                    title='Edit Module',
                    form=form,
                    is_edit=True
                )
        
        module.code = form.code.data.upper()
        module.name = form.name.data
        module.description = form.description.data
        db.session.commit()
        
        flash(f'Module "{module.code}: {module.name}" updated successfully!', 'success')
        return redirect(url_for('module_details', module_id=module.id))
    
    return render_template(
        'lecturer/create_module.html',
        title='Edit Module',
        form=form,
        is_edit=True
    )

@app.route('/lecturer/modules/<int:module_id>/create-test', methods=['GET', 'POST'])
@login_required
def create_test_for_module(module_id):
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to create tests.', 'danger')
        return redirect(url_for('index'))
    
    module = Module.query.get_or_404(module_id)
    
    # Security check - ensure this module belongs to the current lecturer
    if module.lecturer_id != current_user.id:
        abort(403)
    
    form = CreateTestForm()
    form.module_id.data = module.id  # Pre-select the module
    
    if form.validate_on_submit():
        test = Test(
            title=form.title.data,
            description=form.description.data,
            time_limit_minutes=form.time_limit_minutes.data,
            due_date=form.due_date.data,
            max_attempts=form.max_attempts.data,
            passing_score=form.passing_score.data,
            lecturer_id=current_user.id,
            module_id=module.id
        )
        db.session.add(test)
        db.session.commit()
        
        flash(f'Test "{form.title.data}" created successfully!', 'success')
        return redirect(url_for('manage_questions', test_id=test.id))
    
    return render_template(
        'lecturer/create_test.html',
        title='Create Test for Module',
        form=form,
        module=module
    )

# Enrollment route for students
@app.route('/student/enrollment', methods=['GET', 'POST'])
@login_required
def manage_enrollment():
    if not current_user.is_student():
        flash('Access denied: You need to be a student to manage enrollment.', 'danger')
        return redirect(url_for('index'))

    # Query modules
    available_modules = Module.query.order_by(Module.code).all()
    
    # Create a list of choices for the form
    module_choices = []
    for module in available_modules:
        is_enrolled = current_user.is_enrolled_in(module)
        module_choices.append((str(module.id), is_enrolled))

    form = EnrollmentForm()
    form.modules.choices = module_choices

    if request.method == 'GET':
        form.modules.data = [str(m.id) for m in current_user.enrolled_modules]

    if form.validate_on_submit():
        selected_module_ids = [int(m_id) for m_id in form.modules.data]
        
        # Get all current enrollments and new selections
        current_enrollments = current_user.enrolled_modules.all()
        
        # Handle unenrollments
        for module in current_enrollments:
            if module.id not in selected_module_ids:
                current_user.unenroll_from_module(module)
        
        # Handle new enrollments
        for module_id in selected_module_ids:
            module = Module.query.get(module_id)
            if module and not current_user.is_enrolled_in(module):
                current_user.enroll_in_module(module)

        db.session.commit()
        flash('Your course enrollment has been updated successfully!', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template(
        'student/manage_enrollment.html',
        title='Manage Course Enrollment',
        form=form,
        available_modules=available_modules
    )


# Lecturer routes
@app.route('/lecturer/dashboard')
@login_required
def lecturer_dashboard():
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to view this page.', 'danger')
        return redirect(url_for('index'))
    
    # Get all tests for this lecturer
    tests = Test.query.filter_by(lecturer_id=current_user.id).order_by(Test.created_at.desc()).all()
    
    # Get modules taught by this lecturer
    taught_modules = Module.query.filter_by(lecturer_id=current_user.id).all()
    
    # Get all available modules for selection
    all_modules = Module.query.order_by(Module.code).all()
    
    # Count enrolled students in lecturer's modules
    student_count = 0
    for module in taught_modules:
        student_count += module.enrolled_students.count()
    
    return render_template(
        'lecturer/dashboard.html',
        title='Lecturer Dashboard',
        tests=tests,
        modules=taught_modules,
        all_modules=all_modules,
        student_count=student_count
    )

@app.route('/lecturer/create-test', methods=['GET', 'POST'])
@login_required
def create_test():
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to create tests.', 'danger')
        return redirect(url_for('index'))
    
    # Get modules taught by the lecturer for the dropdown
    modules = Module.query.filter_by(lecturer_id=current_user.id).all()
    if not modules:
        flash('You need to create at least one module before creating a test.', 'warning')
        return redirect(url_for('create_module'))
    
    form = CreateTestForm()
    # Populate the module dropdown
    form.module_id.choices = [(m.id, f"{m.code}: {m.name}") for m in modules]
    
    if form.validate_on_submit():
        test = Test(
            title=form.title.data,
            description=form.description.data,
            time_limit_minutes=form.time_limit_minutes.data,
            due_date=form.due_date.data,
            max_attempts=form.max_attempts.data,
            passing_score=form.passing_score.data,
            lecturer_id=current_user.id,
            module_id=form.module_id.data
        )
        db.session.add(test)
        db.session.commit()
        
        flash(f'Test "{form.title.data}" created successfully!', 'success')
        return redirect(url_for('manage_questions', test_id=test.id))
    
    return render_template(
        'lecturer/create_test.html',
        title='Create Test',
        form=form
    )

@app.route('/lecturer/test/<int:test_id>/questions', methods=['GET', 'POST'])
@login_required
def manage_questions(test_id):
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to manage questions.', 'danger')
        return redirect(url_for('index'))
    
    test = Test.query.get_or_404(test_id)
    
    # Security check - ensure this test belongs to the current lecturer
  
    
    form = QuestionForm()
    if form.validate_on_submit():
        question = Question(
            text=form.text.data,
            question_type=form.question_type.data,
            points=form.points.data,
            test_id=test.id
        )
        db.session.add(question)
        db.session.commit()
        
        flash('Question added successfully! Now add some options.', 'success')
        return redirect(url_for('manage_questions', test_id=test.id))
    
    questions = Question.query.filter_by(test_id=test.id).all()
    
    return render_template(
        'lecturer/manage_questions.html',
        title='Manage Questions',
        test=test,
        form=form,
        questions=questions
    )

@app.route('/api/add-option', methods=['POST'])
@login_required
def add_option():
    if not current_user.is_lecturer():
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    question_id = data.get('question_id')
    option_text = data.get('text')
    is_correct = data.get('is_correct', False)
    
    # Verify question exists and belongs to a test owned by this lecturer
    question = Question.query.get_or_404(question_id)
    test = Test.query.get(question.test_id)
    
    if test.lecturer_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Create option
    option = QuestionOption(
        text=option_text,
        is_correct=is_correct,
        question_id=question_id
    )
    db.session.add(option)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "option_id": option.id
    })

@app.route('/lecturer/view-results/<int:test_id>')
@login_required
def view_results(test_id):
    if not current_user.is_lecturer():
        flash('Access denied: You need to be a lecturer to view results.', 'danger')
        return redirect(url_for('index'))
    
    test = Test.query.get_or_404(test_id)
    
    # Security check - ensure this test belongs to the current lecturer

    
    # Get all completed attempts for this test
    attempts = TestAttempt.query.filter_by(
        test_id=test.id,
        is_completed=True
    ).all()
    
    # Get stats for visualization
    num_attempts = len(attempts)
    avg_score = sum(a.score for a in attempts) / num_attempts if num_attempts > 0 else 0
    passing_count = sum(1 for a in attempts if a.score >= test.passing_score)
    passing_rate = (passing_count / num_attempts) * 100 if num_attempts > 0 else 0
    
    # Calculate score distribution for chart
    score_distribution = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    }
    
    for attempt in attempts:
        if attempt.score <= 20:
            score_distribution['0-20'] += 1
        elif attempt.score <= 40:
            score_distribution['21-40'] += 1
        elif attempt.score <= 60:
            score_distribution['41-60'] += 1
        elif attempt.score <= 80:
            score_distribution['61-80'] += 1
        else:
            score_distribution['81-100'] += 1
    
    return render_template(
        'lecturer/view_results.html',
        title=f'Results: {test.title}',
        test=test,
        attempts=attempts,
        num_attempts=num_attempts,
        avg_score=avg_score,
        passing_rate=passing_rate,
        score_distribution=json.dumps(score_distribution)
    )
    
# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    print(f"Admin dashboard accessed by user: {current_user.username}, role: {current_user.role}")
    if not current_user.is_admin():
        print(f"Access denied: User {current_user.username} is not an admin")
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    try:
        print("Getting dashboard stats...")
        # Get counts for dashboard stats
        student_count = User.query.filter_by(role='student').count()
        print(f"Student count: {student_count}")
        
        lecturer_count = User.query.filter_by(role='lecturer').count()
        print(f"Lecturer count: {lecturer_count}")
        
        module_count = Module.query.count()
        print(f"Module count: {module_count}")
        
        test_count = Test.query.count()
        print(f"Test count: {test_count}")
        
        # Get most recent users
        print("Getting recent users...")
        recent_users = User.query.order_by(User.date_registered.desc()).limit(5).all()
        print(f"Found {len(recent_users)} recent users")
        
        print("Rendering admin dashboard template...")
        return render_template(
            'admin/dashboard.html',
            title='Admin Dashboard',
            stats={
                'students': student_count,
                'lecturers': lecturer_count,
                'modules': module_count,
                'tests': test_count
            },
            recent_users=recent_users
        )
    except Exception as e:
        print(f"ERROR in admin_dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_manage_users():
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    filter_form = AdminDashboardFilterForm()
    
    # Process filter form
    if filter_form.validate_on_submit():
        user_type = filter_form.user_type.data
        search_term = filter_form.search.data
        
        # Build base query
        query = User.query
        
        # Apply role filter if not 'all'
        if user_type != 'all':
            query = query.filter_by(role=user_type)
        
        # Apply search filter if provided
        if search_term:
            query = query.filter(
                (User.username.ilike(f'%{search_term}%')) | 
                (User.email.ilike(f'%{search_term}%'))
            )
            
        users = query.order_by(User.username).all()
    else:
        # Default - show all users
        users = User.query.order_by(User.username).all()
    
    return render_template(
        'admin/manage_users.html',
        title='Manage Users',
        users=users,
        filter_form=filter_form
    )

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    form = AdminCreateUserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {user.username} ({user.role}) has been created successfully!', 'success')
        return redirect(url_for('admin_manage_users'))
    
    return render_template(
        'admin/create_user.html',
        title='Create User',
        form=form
    )

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Don't allow editing of own account through this interface
    if user.id == current_user.id:
        flash('You cannot edit your own account through this interface.', 'warning')
        return redirect(url_for('admin_manage_users'))
    
    form = AdminEditUserForm(user.username, user.email)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        
        # Handle password reset if checkbox is checked
        if form.reset_password.data and form.new_password.data:
            user.set_password(form.new_password.data)
            password_reset = True
        else:
            password_reset = False
            
        db.session.commit()
        
        flash_message = f'User {user.username} updated successfully!'
        if password_reset:
            flash_message += ' Password has been reset.'
            
        flash(flash_message, 'success')
        return redirect(url_for('admin_manage_users'))
    
    # Pre-populate form with current user data
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.role.data = user.role
    
    return render_template(
        'admin/edit_user.html',
        title=f'Edit User: {user.username}',
        form=form,
        user=user
    )

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Don't allow deletion of own account
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_manage_users'))
    
    # Don't allow deletion of the last admin
    if user.is_admin() and User.query.filter_by(role='admin').count() <= 1:
        flash('Cannot delete the last administrator account.', 'danger')
        return redirect(url_for('admin_manage_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been deleted successfully.', 'success')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/modules', methods=['GET'])
@login_required
def admin_manage_modules():
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    modules = Module.query.order_by(Module.code).all()
    
    return render_template(
        'admin/manage_modules.html',
        title='Manage Modules',
        modules=modules
    )

@app.route('/admin/modules/create', methods=['GET', 'POST'])
@login_required
def admin_create_module():
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    form = AdminCreateModuleForm()
    
    # Populate lecturer choices
    lecturers = User.query.filter_by(role='lecturer').order_by(User.username).all()
    form.lecturer_id.choices = [(l.id, f"{l.username} ({l.email})") for l in lecturers]
    
    if form.validate_on_submit():
        module = Module(
            code=form.code.data.upper(),
            name=form.name.data,
            description=form.description.data,
            lecturer_id=form.lecturer_id.data
        )
        db.session.add(module)
        db.session.commit()
        
        flash(f'Module "{module.code}: {module.name}" created successfully!', 'success')
        return redirect(url_for('admin_manage_modules'))
    
    return render_template(
        'admin/create_module.html',
        title='Create Module',
        form=form
    )

@app.route('/admin/modules/edit/<int:module_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_module(module_id):
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    module = Module.query.get_or_404(module_id)
    
    # Create a custom form for editing - similar to create form but without code validation
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, SelectField, SubmitField
    from wtforms.validators import DataRequired, Length, Optional
    
    class AdminEditModuleForm(FlaskForm):
        code = StringField('Module Code', validators=[DataRequired(), Length(max=10)])
        name = StringField('Module Name', validators=[DataRequired(), Length(max=100)])
        description = TextAreaField('Description', validators=[Optional()])
        lecturer_id = SelectField('Assign to Lecturer', coerce=int, validators=[DataRequired()])
        submit = SubmitField('Save Changes')
    
    form = AdminEditModuleForm()
    
    # Populate lecturer choices
    lecturers = User.query.filter_by(role='lecturer').order_by(User.username).all()
    form.lecturer_id.choices = [(l.id, f"{l.username} ({l.email})") for l in lecturers]
    
    if form.validate_on_submit():
        # Check if code is changed and if it conflicts with existing code
        if form.code.data.upper() != module.code:
            existing_module = Module.query.filter_by(code=form.code.data.upper()).first()
            if existing_module:
                form.code.errors.append('That module code is already in use. Please choose a different one.')
                return render_template(
                    'admin/edit_module.html',
                    title=f'Edit Module: {module.code}',
                    form=form,
                    module=module
                )
        
        module.code = form.code.data.upper()
        module.name = form.name.data
        module.description = form.description.data
        module.lecturer_id = form.lecturer_id.data
        
        db.session.commit()
        
        flash(f'Module "{module.code}: {module.name}" updated successfully!', 'success')
        return redirect(url_for('admin_manage_modules'))
    
    # Pre-populate form with current module data
    if request.method == 'GET':
        form.code.data = module.code
        form.name.data = module.name
        form.description.data = module.description
        form.lecturer_id.data = module.lecturer_id
    
    return render_template(
        'admin/edit_module.html',
        title=f'Edit Module: {module.code}',
        form=form,
        module=module
    )

@app.route('/admin/modules/delete/<int:module_id>', methods=['POST'])
@login_required
def admin_delete_module(module_id):
    if not current_user.is_admin():
        flash('Access denied: You need to be an administrator to access this page.', 'danger')
        return redirect(url_for('index'))
    
    module = Module.query.get_or_404(module_id)
    
    # Check if module has tests - prevent deletion if it does
    if module.tests:
        flash(f'Cannot delete module "{module.code}" because it has associated tests. Remove all tests first.', 'danger')
        return redirect(url_for('admin_manage_modules'))
    
    module_code = module.code
    db.session.delete(module)
    db.session.commit()
    
    flash(f'Module "{module_code}" has been deleted successfully.', 'success')
    return redirect(url_for('admin_manage_modules'))
