"""
Seed initial data: Request Types + default Admin/Approver/Employee accounts.
Run once: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import User, RequestType, UserRole
from app.auth import hash_password

Base.metadata.create_all(bind=engine)


def seed():
    db = SessionLocal()
    try:
        # ── Request Types ──────────────────────────────────────────────────────
        request_types = [
            {
                "name": "System Access Request",
                "description": "Access to an application, shared folder, or internal tool",
                "requires_approval": True,
                "turnaround_days": 3,
            },
            {
                "name": "Equipment Request",
                "description": "Laptop, monitor, headset, ID card replacement, peripherals",
                "requires_approval": True,
                "turnaround_days": 5,
            },
            {
                "name": "Facility Request",
                "description": "Meeting room booking, parking access, visitor pass",
                "requires_approval": False,
                "turnaround_days": 2,
            },
            {
                "name": "General Service Request",
                "description": "Workspace change, seating issue, basic support need",
                "requires_approval": False,
                "turnaround_days": 3,
            },
        ]
        for rt_data in request_types:
            existing = db.query(RequestType).filter(RequestType.name == rt_data["name"]).first()
            if not existing:
                db.add(RequestType(**rt_data))
                print(f"  ✓ Created request type: {rt_data['name']}")
            else:
                print(f"  ─ Skipping existing request type: {rt_data['name']}")

        # ── Default Users ──────────────────────────────────────────────────────
        default_users = [
            {
                "name": "System Admin",
                "email": "admin@company.com",
                "password": "Admin@1234",
                "role": UserRole.admin,
                "manager_email": None,
            },
            {
                "name": "Priya Approver",
                "email": "approver@company.com",
                "password": "Approver@1234",
                "role": UserRole.approver,
                "manager_email": "admin@company.com",
            },
            {
                "name": "Arjun Employee",
                "email": "employee@company.com",
                "password": "Employee@1234",
                "role": UserRole.employee,
                "manager_email": "approver@company.com",
            },
        ]
        for u_data in default_users:
            existing = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing:
                user = User(
                    name=u_data["name"],
                    email=u_data["email"],
                    hashed_password=hash_password(u_data["password"]),
                    role=u_data["role"],
                    manager_email=u_data.get("manager_email"),
                )
                db.add(user)
                print(f"  ✓ Created user: {u_data['email']} ({u_data['role'].value})")
            else:
                print(f"  ─ Skipping existing user: {u_data['email']}")

        db.commit()
        print("\n✅ Seed complete.")
    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding Nila database...\n")
    seed()
