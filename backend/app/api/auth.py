"""JWT authentication with MongoDB persistence (configured through environment variables)."""
import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from jose import jwt
import bcrypt

router = APIRouter(prefix='/auth', tags=['auth'])
SECRET = os.getenv('JWT_SECRET', 'change-this-secret-in-production')
ALGORITHM = 'HS256'
from pathlib import Path
import sqlite3
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
SECRET = os.getenv('JWT_SECRET', 'change-this-secret-in-production')
_mongo_uri = os.getenv('MONGODB_URI')
_users = MongoClient(_mongo_uri, serverSelectionTimeoutMS=3000)[os.getenv('MONGODB_DATABASE', 'dcare')].users if _mongo_uri else None
_local_db = Path(__file__).resolve().parents[2] / 'outputs' / 'auth.sqlite3'

def local_connection():
    _local_db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(_local_db)
    connection.row_factory = sqlite3.Row
    connection.execute('CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, password_hash TEXT, role TEXT)')
    columns = {row[1] for row in connection.execute('PRAGMA table_info(users)')}
    for column, definition in [('username', 'TEXT'), ('phone', 'TEXT'), ('is_diabetic', 'INTEGER')]:
        if column not in columns:
            connection.execute(f'ALTER TABLE users ADD COLUMN {column} {definition}')
    connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users(username)')
    return connection

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=80)

    @field_validator('password')
    @classmethod
    def validate_password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes.')
        return value

class Registration(Credentials):
    username: str = Field(min_length=3, max_length=30, pattern=r'^[A-Za-z0-9_]+$')
    phone: str = Field(pattern=r'^07[0-9]{8}$')
    is_diabetic: bool

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

def token_for(user):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(user['email']), 'role': user.get('role', 'patient'), 'iat': now, 'exp': now + timedelta(hours=12)}, SECRET, algorithm=ALGORITHM)

def find(email):
    try:
        if _users is not None:
            return _users.find_one({'email': email})
        with local_connection() as connection:
            row = connection.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            return dict(row) if row else None
    except (PyMongoError, sqlite3.Error):
        raise HTTPException(status_code=503, detail='Account database is unavailable. Please try again later.')

def save(user):
    try:
        if _users is not None:
            _users.create_index('email', unique=True)
            _users.create_index('username', unique=True, sparse=True)
            _users.insert_one(user)
        else:
            with local_connection() as connection:
                connection.execute('INSERT INTO users (email, name, password_hash, role, username, phone, is_diabetic) VALUES (?, ?, ?, ?, ?, ?, ?)', (user['email'], user['name'], user['password_hash'], user['role'], user['username'], user['phone'], int(user['is_diabetic'])))
    except (DuplicateKeyError, sqlite3.IntegrityError):
        raise HTTPException(status_code=409, detail='Email or username is already registered.')
    except (PyMongoError, sqlite3.Error):
        raise HTTPException(status_code=503, detail='Account database is unavailable. Please try again later.')

@router.post('/register')
def register(payload: Registration):
    email = payload.email.lower()
    if find(email): raise HTTPException(status_code=409, detail='An account with this email already exists.')
    user = {'email': email, 'name': payload.name or email.split('@')[0], 'password_hash': bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('ascii'), 'role': 'patient', 'username': payload.username, 'phone': payload.phone, 'is_diabetic': payload.is_diabetic}
    save(user); return {'access_token': token_for(user), 'token_type': 'bearer'}

@router.post('/login')
def login(payload: Credentials):
    user = find(payload.email.lower())
    if not user or not bcrypt.checkpw(payload.password.encode('utf-8'), user['password_hash'].encode('ascii')): raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid email or password.')
    return {'access_token': token_for(user), 'token_type': 'bearer'}
