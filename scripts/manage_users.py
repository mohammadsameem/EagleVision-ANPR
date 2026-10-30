"""
User and API key management script for EagleVision ANPR

Usage:
    python scripts/manage_users.py create-user <username> <email> [--admin]
    python scripts/manage_users.py create-api-key <username> [--name "My Key"] [--expires-days 365]
    python scripts/manage_users.py list-users
    python scripts/manage_users.py list-api-keys <username>
    python scripts/manage_users.py revoke-api-key <key_prefix>
"""
import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SessionLocal, init_db
from src.auth import User, APIKey, create_api_key


def create_user(username: str, email: str, is_admin: bool = False) -> User:
    """Create a new user"""
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            print(f"❌ User already exists: {existing.username} ({existing.email})")
            return None
        
        # Create user
        user = User(
            username=username,
            email=email,
            is_active=True,
            is_admin=is_admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ User created:")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Admin: {user.is_admin}")
        print(f"   Created: {user.created_at}")
        
        return user
    finally:
        db.close()


def create_user_api_key(username: str, key_name: str = None, expires_days: int = None) -> None:
    """Create API key for user"""
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ User not found: {username}")
            return
        
        # Create API key
        api_key, raw_key = create_api_key(
            db,
            user_id=user.id,
            name=key_name,
            expires_in_days=expires_days
        )
        
        print(f"✅ API key created:")
        print(f"   User: {user.username} (ID: {user.id})")
        print(f"   Name: {api_key.name or '(unnamed)'}")
        print(f"   Expires: {api_key.expires_at or 'Never'}")
        print(f"   Created: {api_key.created_at}")
        print()
        print(f"🔑 API Key (save this, it won't be shown again):")
        print(f"   {raw_key}")
        print()
        print(f"Use this key in API requests:")
        print(f'   curl -H "X-API-Key: {raw_key}" http://localhost:8000/api/videos/')
        
    finally:
        db.close()


def list_users() -> None:
    """List all users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        
        if not users:
            print("No users found")
            return
        
        print(f"Users ({len(users)}):")
        print("-" * 80)
        for user in users:
            api_key_count = len(user.api_keys)
            video_count = len(user.videos)
            print(f"ID: {user.id}")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Active: {user.is_active}")
            print(f"  Admin: {user.is_admin}")
            print(f"  API Keys: {api_key_count}")
            print(f"  Videos: {video_count}")
            print(f"  Created: {user.created_at}")
            print(f"  Last Login: {user.last_login_at or 'Never'}")
            print()
    finally:
        db.close()


def list_user_api_keys(username: str) -> None:
    """List API keys for a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ User not found: {username}")
            return
        
        keys = user.api_keys
        
        if not keys:
            print(f"No API keys for user: {username}")
            return
        
        print(f"API Keys for {username} ({len(keys)}):")
        print("-" * 80)
        for key in keys:
            status = "✅ Active" if key.is_active else "❌ Revoked"
            expired = ""
            if key.expires_at:
                from datetime import datetime
                if key.expires_at < datetime.utcnow():
                    expired = " (EXPIRED)"
            
            print(f"ID: {key.id}")
            print(f"  Prefix: {key.key_prefix}...")
            print(f"  Name: {key.name or '(unnamed)'}")
            print(f"  Status: {status}{expired}")
            print(f"  Created: {key.created_at}")
            print(f"  Last Used: {key.last_used_at or 'Never'}")
            print(f"  Expires: {key.expires_at or 'Never'}")
            print()
    finally:
        db.close()


def revoke_api_key(key_prefix: str) -> None:
    """Revoke an API key by prefix"""
    db = SessionLocal()
    try:
        key = db.query(APIKey).filter(APIKey.key_prefix == key_prefix).first()
        
        if not key:
            print(f"❌ API key not found with prefix: {key_prefix}")
            return
        
        key.is_active = False
        db.commit()
        
        print(f"✅ API key revoked:")
        print(f"   Prefix: {key.key_prefix}...")
        print(f"   Name: {key.name or '(unnamed)'}")
        print(f"   User: {key.user.username}")
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="EagleVision ANPR User Management")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # create-user
    create_user_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_user_parser.add_argument("username", help="Username")
    create_user_parser.add_argument("email", help="Email address")
    create_user_parser.add_argument("--admin", action="store_true", help="Create as admin")
    
    # create-api-key
    create_key_parser = subparsers.add_parser("create-api-key", help="Create API key for user")
    create_key_parser.add_argument("username", help="Username")
    create_key_parser.add_argument("--name", help="Key name/description")
    create_key_parser.add_argument("--expires-days", type=int, help="Days until expiration")
    
    # list-users
    subparsers.add_parser("list-users", help="List all users")
    
    # list-api-keys
    list_keys_parser = subparsers.add_parser("list-api-keys", help="List API keys for user")
    list_keys_parser.add_argument("username", help="Username")
    
    # revoke-api-key
    revoke_parser = subparsers.add_parser("revoke-api-key", help="Revoke an API key")
    revoke_parser.add_argument("key_prefix", help="API key prefix (first 8 characters)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize database
    print("Initializing database...")
    init_db()
    print()
    
    # Execute command
    if args.command == "create-user":
        create_user(args.username, args.email, args.admin)
    
    elif args.command == "create-api-key":
        create_user_api_key(args.username, args.name, args.expires_days)
    
    elif args.command == "list-users":
        list_users()
    
    elif args.command == "list-api-keys":
        list_user_api_keys(args.username)
    
    elif args.command == "revoke-api-key":
        revoke_api_key(args.key_prefix)


if __name__ == "__main__":
    main()
