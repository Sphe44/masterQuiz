"""
Database seeding script for the Online Test Platform.
This script populates the database with initial courses, modules, and admin user.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Module

def create_admin(username, email, password):
    """Create a new admin user"""
    admin = User(
        username=username,
        email=email,
        role="admin",
        date_registered=datetime.utcnow()
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f"Admin user {username} created successfully!")

def seed_database():
    """
    Seed the database with initial data.
    Only runs if the database is empty (no users found).
    """
    # Check if database already has data
    user_count = User.query.count()
    if user_count > 0:
        print("Database already has data. Skipping seeding.")
        return
    
    print("Seeding database with initial data...")
    
    # Create admin user
    admin_user = User(
        username="admin",
        email="admin@example.com",
        role="admin",
        date_registered=datetime.utcnow()
    )
    admin_user.set_password("admin123")  # In production, use a secure password
    
    # Create lecturer accounts
    lecturers = [
        {
            "username": "prof_smith",
            "email": "smith@example.com",
            "password": "lecturer123",
            "modules": [
                {"code": "CS101", "name": "Introduction to Computer Science", 
                 "description": "A foundational course covering the basic concepts of computer science."},
                {"code": "CS201", "name": "Data Structures", 
                 "description": "Learn about fundamental data structures and their implementation."}
            ]
        },
        {
            "username": "prof_jones",
            "email": "jones@example.com",
            "password": "lecturer123",
            "modules": [
                {"code": "IT301", "name": "Web Development", 
                 "description": "Learn to build modern web applications using current technologies."},
                {"code": "IT401", "name": "Mobile App Development", 
                 "description": "Introduction to building mobile applications for iOS and Android."}
            ]
        },
        {
            "username": "prof_zhang",
            "email": "zhang@example.com",
            "password": "lecturer123",
            "modules": [
                {"code": "MATH101", "name": "Calculus I", 
                 "description": "Introduction to differential and integral calculus."},
                {"code": "MATH201", "name": "Linear Algebra", 
                 "description": "Study of vectors, matrices, and linear equations."}
            ]
        }
    ]
    
    # Add all users to database
    db.session.add(admin_user)
    
    # Create the lecturers and their modules
    for lecturer_data in lecturers:
        lecturer = User(
            username=lecturer_data["username"],
            email=lecturer_data["email"],
            role="lecturer",
            date_registered=datetime.utcnow()
        )
        lecturer.set_password(lecturer_data["password"])
        db.session.add(lecturer)
        db.session.flush()  # Flush to get the lecturer ID
        
        # Create modules for this lecturer
        for module_data in lecturer_data["modules"]:
            module = Module(
                code=module_data["code"],
                name=module_data["name"],
                description=module_data["description"],
                lecturer_id=lecturer.id,
                created_at=datetime.utcnow()
            )
            db.session.add(module)
    
    # Create some sample students
    students = [
        {"username": "student1", "email": "student1@example.com", "password": "student123"},
        {"username": "student2", "email": "student2@example.com", "password": "student123"},
        {"username": "student3", "email": "student3@example.com", "password": "student123"}
    ]
    
    for student_data in students:
        student = User(
            username=student_data["username"],
            email=student_data["email"],
            role="student",
            date_registered=datetime.utcnow()
        )
        student.set_password(student_data["password"])
        db.session.add(student)
    
    # Commit all changes
    db.session.commit()
    print("Database seeded successfully!")

# Only run when script is executed directly
if __name__ == "__main__":
    with app.app_context():
        seed_database()