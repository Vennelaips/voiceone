import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "voiceone-secure-civic-secret-key-2026-xyz892")
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/voiceone_db")
    DB_NAME = os.environ.get("DB_NAME", "voiceone_db")
    
    # DigiLocker OAuth 2.0 Credentials (Sandbox & Production)
    DIGILOCKER_CLIENT_ID = os.environ.get("DIGILOCKER_CLIENT_ID", "VOICEONE_DL_SANDBOX_ID")
    DIGILOCKER_CLIENT_SECRET = os.environ.get("DIGILOCKER_CLIENT_SECRET", "VOICEONE_DL_SANDBOX_SECRET")
    DIGILOCKER_REDIRECT_URI = os.environ.get("DIGILOCKER_REDIRECT_URI", "http://127.0.0.1:5000/auth/digilocker/callback")
    DIGILOCKER_AUTH_URL = os.environ.get("DIGILOCKER_AUTH_URL", "https://api.digitallocker.gov.in/public/oauth2/1/authorize")
    DIGILOCKER_TOKEN_URL = os.environ.get("DIGILOCKER_TOKEN_URL", "https://api.digitallocker.gov.in/public/oauth2/1/token")
    DIGILOCKER_USERINFO_URL = os.environ.get("DIGILOCKER_USERINFO_URL", "https://api.digitallocker.gov.in/public/oauth2/1/user")
    
    # Cryptographic Salt for Aadhaar Anonymization
    AADHAAR_HASH_SALT = os.environ.get("AADHAAR_HASH_SALT", "voiceone_civic_privacy_salt_v1_9a8b7c6d")
    
    # Server & Port for Render deployment
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
