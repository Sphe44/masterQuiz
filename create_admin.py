
from app import app, db
from seed_db import create_admin

# Create a new admin user
with app.app_context():
    create_admin(
        username="newadmin",
        email="newadmin@example.com", 
        password="admin123"
    )
