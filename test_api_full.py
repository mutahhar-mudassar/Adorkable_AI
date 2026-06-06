#!/usr/bin/env python3
"""Full API test to find the error"""
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from datetime import datetime, timedelta
from jose import jwt
from backend.config import SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from backend.database import get_db, create_all_tables, User, get_user_by_email
from backend.auth import hash_password, UserOut, Token
from sqlalchemy.ext.asyncio import AsyncSession

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)

async def test_full_register():
    print("🧪 Testing FULL registration flow...")
    
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        email = "mutahharmudassar@gmail.com"
        password = "mutahhar"
        
        # Check existing
        print("1️⃣ Checking existing user...")
        existing = await get_user_by_email(db, email)
        if existing:
            print(f"   User exists: {existing.id}")
            user = existing
        else:
            # Create user
            print("2️⃣ Creating new user...")
            hashed_pw = hash_password(password)
            print(f"   Password hashed: {hashed_pw[:20]}...")
            
            new_user = User(
                email=email,
                hashed_password=hashed_pw,
                gender="Male",
                city="Lahore"
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            user = new_user
            print(f"   User created: ID={user.id}")
        
        # Create token
        print("3️⃣ Creating access token...")
        access_token = create_access_token(data={"sub": user.id})
        print(f"   Token created: {access_token[:30]}...")
        
        # Create UserOut with Pydantic
        print("4️⃣ Creating UserOut model...")
        try:
            user_out = UserOut.model_validate(user)
            print(f"   UserOut created: id={user_out.id}, email={user_out.email}")
        except Exception as e:
            print(f"   ❌ UserOut error: {e}")
            raise
        
        # Create Token
        print("5️⃣ Creating Token response...")
        try:
            token_response = Token(
                access_token=access_token,
                token_type="bearer",
                user=user_out
            )
            print(f"   Token response created successfully!")
            print(f"\n🎉 SUCCESS! Full flow works!")
        except Exception as e:
            print(f"   ❌ Token error: {e}")
            raise
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        print("\n🔴 Full traceback:")
        traceback.print_exc()
    finally:
        await db.close()
        print("\n🔒 Session closed")

if __name__ == "__main__":
    asyncio.run(test_full_register())
