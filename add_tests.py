"""
Script to add additional tests to existing modules.
"""
from app import app, db
from models import Test, Question, QuestionOption, Module, User
from datetime import datetime, timedelta

def add_tests():
    """
    Add additional tests to modules.
    """
    print("Adding tests to modules...")

    # Get lecturer from the database
    lecturer = User.query.filter_by(role="lecturer").first()
    if not lecturer:
        print("No lecturer found in the database. Aborting.")
        return

    # Get existing modules
    modules = Module.query.all()
    if not modules:
        print("No modules found. Aborting.")
        return

    # Clear existing tests
    Test.query.delete()
    db.session.commit()

    for module in modules:
        # Create 5 tests for each module
        for i in range(1, 6):
            test = Test(
                title=f"{module.code} Test {i}",
                description=f"Test {i} for {module.name}",
                time_limit_minutes=45,
                due_date=datetime.utcnow() + timedelta(days=14 + i),
                max_attempts=2,
                passing_score=70,
                module=module,
                lecturer_id=lecturer.id
            )
            db.session.add(test)
            db.session.flush()  # Get test ID

            # Add 3 questions per test
            for j in range(1, 4):
                question = Question(
                    text=f"Question {j} for {module.code} Test {i}",
                    question_type="multiple_choice",
                    points=5,
                    test=test
                )
                db.session.add(question)
                db.session.flush()  # Get question ID

                # Add 4 options per question
                options = [
                    (f"Option A for Q{j}", j == 1),  # First option is correct
                    (f"Option B for Q{j}", False),
                    (f"Option C for Q{j}", False),
                    (f"Option D for Q{j}", False)
                ]

                for text, is_correct in options:
                    option = QuestionOption(
                        text=text,
                        is_correct=is_correct,
                        question=question
                    )
                    db.session.add(option)

    db.session.commit()
    print("Successfully added tests to all modules!")

if __name__ == "__main__":
    with app.app_context():
        add_tests()