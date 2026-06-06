#!/usr/bin/env python3
"""Debug script to test registration and see full error"""
import sys
import os
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
from backend.database import get_db, create_all_tables, User, get_user_by_email
from backend.auth import hash_password, create_access_token
from sqlalchemy.ext.asyncio import AsyncSession

async def test_register():
    """Test user registration directly"""
    print("🧪 Testing registration...")
    
    # Create tables first
    await create_all_tables()
    print("✅ Tables created")
    
    # Get database session
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        email = "test@example.com"
        password = "password123"
        
        # Check if user exists
        print(f"🔍 Checking if user exists: {email}")
        existing = await get_user_by_email(db, email)
        if existing:
            print(f"⚠️ User already exists: {existing.email}")
            return
        
        # Create new user
        print("📝 Creating new user...")
        hashed_pw = hash_password(password)
        new_user = User(
            email=email,
            hashed_password=hashed_pw,
            gender="Male",
            city="Lahore"
        )
        
        db.add(new_user)
        print("💾 Added user to session")
        
        await db.commit()
        print("✅ Committed to database")
        
        await db.refresh(new_user)
        print(f"✅ User created with ID: {new_user.id}")
        
        # Create token
        token = create_access_token(data={"sub": new_user.id})
        print(f"✅ Token created: {token[:50]}...")
        
        print("\n🎉 SUCCESS! Registration works!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        print("\n🔴 Full traceback:")
        traceback.print_exc()
        
        # Rollback
        try:
            await db.rollback()
            print("✅ Rolled back")
        except:
            pass
    finally:
        await db.close()
        print("🔒 Session closed")

if __name__ == "__main__":
    asyncio.run(test_register())
