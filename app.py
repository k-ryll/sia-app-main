from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from transformers import pipeline
from datetime import datetime, timedelta
from langdetect import detect, DetectorFactory
from pymongo import MongoClient
from bson import ObjectId
from passlib.context import CryptContext
import jwt
import threading
import os

# Force Transformers to use PyTorch only to avoid tf-keras requirement
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")


DetectorFactory.seed = 0
app = FastAPI(title="GabayLakbay Translation + Auth")

SECRET_KEY = "supersecretkey"  # ⚠️ change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
client = MongoClient(mongodb_url)
db = client["gabaylakbay"]
tokens_collection = db["tokens"]
api_tokens_collection = db["api_tokens"]
users_collection = db["users"]
messages_raw = db["messages_raw"]
messages_translated = db["messages_translated"]

# --- CORS ---

cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://72.60.194.243:3000"

]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------
# Auth Models & Utils
# ----------------------------
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check in DB
        token_doc = tokens_collection.find_one({"token": token})
        if not token_doc:
            raise HTTPException(status_code=401, detail="Token not found or revoked")
        if token_doc["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token expired")

        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ----------------------------
# Auth Endpoints
# ----------------------------
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/auth/signup")
def signup(user: UserCreate):
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pw = get_password_hash(user.password)
    users_collection.insert_one({"username": user.username, "password": hashed_pw})
    return {"message": "User created successfully"}

from uuid import uuid4

@app.post("/auth/login", response_model=Token)
def login(user: UserLogin):
    user_in_db = users_collection.find_one({"username": user.username})
    if not user_in_db or not verify_password(user.password, user_in_db["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Generate JWT
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Save JWT in DB
    tokens_collection.insert_one({
        "username": user.username,
        "token": access_token,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
    })

    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/generate-token")
def generate_api_token(username: str = Depends(get_current_user)):
    # Expiration: 30 days
    expires_at = datetime.utcnow() + timedelta(days=30)

    # Generate random API token
    token_value = str(uuid4())

    api_tokens_collection.insert_one({
        "username": username,
        "token": token_value,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at
    })

    return {
        "token": token_value,
        "expires_at": expires_at.isoformat()
    }

@app.get("/auth/my-tokens")
def list_tokens(username: str = Depends(get_current_user)):
    api_tokens = list(api_tokens_collection.find({"username": username}))
    return {
        "api_tokens": [
            {
                "id": str(t["_id"]),
                "token": t["token"],
                "created_at": t["created_at"].isoformat(),
                "expires_at": t["expires_at"].isoformat(),
            }
            for t in api_tokens
        ]
    }

@app.delete("/auth/delete-token/{token_id}")
def delete_token(token_id: str, username: str = Depends(get_current_user)):
    result = api_tokens_collection.delete_one({"_id": ObjectId(token_id), "username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"message": "Token deleted successfully"}

# ----------------------------
# Verify API Token Dependency
# ----------------------------
def get_api_user(token: str):
    record = api_tokens_collection.find_one({"token": token})
    if not record:
        raise HTTPException(status_code=401, detail="Invalid API token")
    if record["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
    return record["username"]

# Example: Protect API with API token instead of login JWT
@app.get("/protected-api")
def protected_api(api_token: str):
    user = get_api_user(api_token)
    return {"message": f"Hello {user}, you accessed the API with a valid token!"}

def get_authenticated_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username:
            return username
    except jwt.PyJWTError:
        pass  

    record = api_tokens_collection.find_one({"token": token})
    if record and record["expires_at"] > datetime.utcnow():
        return record["username"]

    raise HTTPException(status_code=401, detail="Not authenticated")



def get_api_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="API token required")
    
    token = authorization.split(" ")[1]
    token_data = api_tokens_collection.find_one({"token": token})
    
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or revoked API token")
    
    # check expiry
    if token_data["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
    
    return token_data["username"]

SUPPORTED_LANGS = ["en", "fil", "ceb", "ilo", "pag", "zh", "ja", "ko"]

# Primary model map - using better models for Filipino
MODEL_MAP = {
    # Use NLLB for much better Filipino translation quality
    ("en", "fil"): "facebook/nllb-200-distilled-600M",
    ("fil", "en"): "facebook/nllb-200-distilled-600M",
    ("en", "ja"): "Helsinki-NLP/opus-mt-en-jap",
    ("ja", "en"): "Helsinki-NLP/opus-mt-jap-en",
    ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
    ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
    ("en", "ko"): "facebook/nllb-200-distilled-600M",
    ("ko", "en"): "facebook/nllb-200-distilled-600M",
    ("en", "pag"): "Helsinki-NLP/opus-mt-en-pag",
    ("pag", "en"): "Helsinki-NLP/opus-mt-pag-en",
    ("en", "ilo"): "Helsinki-NLP/opus-mt-en-ilo",
    ("ilo", "en"): "Helsinki-NLP/opus-mt-ilo-en",
    ("en", "ceb"): "Helsinki-NLP/opus-mt-en-ceb",
    ("ceb", "en"): "Helsinki-NLP/opus-mt-ceb-en",
}

# Alternative models for Filipino (can be switched via environment variable)
FILIPINO_ALTERNATIVES = {
    "nllb": "facebook/nllb-200-distilled-600M",  # Default - much better quality
    "nllb-large": "facebook/nllb-200-3.3B",     # Larger NLLB model - even better quality
    "opus": "Helsinki-NLP/opus-mt-en-tl",        # Original - poor quality
    "opus-large": "Helsinki-NLP/opus-mt-en-tl",  # Same as opus
}

def get_filipino_model():
    """Get the Filipino translation model based on environment variable"""
    model_choice = os.getenv("FILIPINO_MODEL", "nllb").lower()
    return FILIPINO_ALTERNATIVES.get(model_choice, FILIPINO_ALTERNATIVES["nllb"])

TRANSLATORS = {}
# --- Language code mappings for NLLB ---
NLLB_LANG_CODES = {
    "en": "eng_Latn",
    "ko": "kor_Hang",
    "ja": "jpn_Jpan",
    "zh": "zho_Hans",   # use "zho_Hant" if you want Traditional
    "fil": "tgl_Latn",  # Tagalog/Filipino in NLLB
    "ceb": "ceb_Latn",  # Cebuano
    "ilo": "ilo_Latn",  # Ilocano
    "pag": "pag_Latn",  # Pangasinan
}

TRANSLATORS = {}

def get_filipino_model():
    model_choice = os.getenv("FILIPINO_MODEL", "nllb").lower()
    return FILIPINO_ALTERNATIVES.get(model_choice, FILIPINO_ALTERNATIVES["nllb"])

def get_translator(src_lang: str, tgt_lang: str):
    if (src_lang, tgt_lang) in [("en", "fil"), ("fil", "en")]:
        model = get_filipino_model()
    elif (src_lang, tgt_lang) not in MODEL_MAP:
        return None
    else:
        model = MODEL_MAP[(src_lang, tgt_lang)]
    if (src_lang, tgt_lang) not in TRANSLATORS:
        TRANSLATORS[(src_lang, tgt_lang)] = pipeline("translation", model=model)
    return TRANSLATORS[(src_lang, tgt_lang)]

def run_translation(text: str, src_lang: str, tgt_lang: str):
    translator = get_translator(src_lang, tgt_lang)
    if not translator:
        return None
    model_name = translator.model.config.name_or_path.lower()
    if "nllb" in model_name:
        src_code = NLLB_LANG_CODES.get(src_lang)
        tgt_code = NLLB_LANG_CODES.get(tgt_lang)
        if not src_code or not tgt_code:
            return None
        return translator(text, src_lang=src_code, tgt_lang=tgt_code)[0]["translation_text"]
    return translator(text)[0]["translation_text"]




class MessageRequest(BaseModel):
    text: str
    target_lang: str = "en"  # Default target language for immediate translation


@app.post("/send")
def send_message(req: MessageRequest, username: str = Depends(get_authenticated_user)):
    try:
        # Detect language quickly
        src_lang = detect(req.text).lower()
        if src_lang == "tl": 
            src_lang = "fil"

        # Insert raw message immediately
        raw_doc = {
            "original": req.text,
            "source_lang": src_lang,
            "user": username,
            "timestamp": datetime.utcnow()
        }
        inserted = messages_raw.insert_one(raw_doc)

        # Get immediate translation for the target language
        immediate_translation = None
        if req.target_lang != src_lang:
            try:
                immediate_translation = run_translation(req.text, src_lang, req.target_lang)
                if not immediate_translation and src_lang != "en" and req.target_lang != "en":
                    # Try via English if direct translation fails
                    to_en = run_translation(req.text, src_lang, "en")
                    if to_en:
                        immediate_translation = run_translation(to_en, "en", req.target_lang)
            except Exception as e:
                print(f"Translation error: {e}")
                immediate_translation = None
        
        # Use original text if translation failed or same language
        if not immediate_translation:
            immediate_translation = req.text

        # Persist the immediate translation so it is available after refresh
        try:
            translations_set = {
                f"translations.{src_lang}": req.text,
                f"translations.{req.target_lang}": immediate_translation,
            }
            messages_translated.update_one(
                {"message_id": str(inserted.inserted_id)},
                {
                    "$set": translations_set,
                    "$setOnInsert": {
                        "message_id": str(inserted.inserted_id),
                        "timestamp": datetime.utcnow(),
                    },
                },
                upsert=True,
            )
        except Exception as e:
            print(f"Warning: failed to upsert immediate translation: {e}")
        
        # Kick off translation in background thread for all other languages
        def do_translations(message_id, text, src_lang, target_lang, immediate_translation):
            try:
                translations = {}
                for lang in SUPPORTED_LANGS:
                    if lang == src_lang:
                        translations[lang] = text
                    elif lang == target_lang:
                        # Use the already computed immediate translation
                        translations[lang] = immediate_translation
                    else:
                        result = run_translation(text, src_lang, lang)
                        if not result and src_lang != "en" and lang != "en":
                            to_en = run_translation(text, src_lang, "en")
                            if to_en:
                                result = run_translation(to_en, "en", lang)
                        translations[lang] = result or text

                translated_doc = {
                    "message_id": message_id,
                    "translations": translations,
                    "timestamp": datetime.utcnow()
                }
                messages_translated.insert_one(translated_doc)
            except Exception as e:
                print(f"Error in background translations: {e}")
                import traceback
                traceback.print_exc()

        threading.Thread(
            target=do_translations, 
            args=(str(inserted.inserted_id), req.text, src_lang, req.target_lang, immediate_translation),
            daemon=True
        ).start()

        # ✅ Return immediately with raw message and live translation
        return {
            "status": "ok",
            "message": {
                "id": str(inserted.inserted_id),
                "original": raw_doc["original"],
                "source_lang": raw_doc["source_lang"],
                "translation": immediate_translation,
                "target_lang": req.target_lang,
                "timestamp": raw_doc["timestamp"].isoformat()
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/messages")
def get_messages(lang: str = "en", username: str = Depends(get_authenticated_user)):
    try:
        results = []
        cursor = messages_raw.find({"user": username}).sort("timestamp", -1)
        for msg in cursor:
            translated = messages_translated.find_one({"message_id": str(msg["_id"])})
            translation_text = None
            translations_map = translated.get("translations", {}) if translated else {}

            # Prefer requested language
            translation_text = translations_map.get(lang)

            # If missing, compute on-the-fly, persist, and use it
            if not translation_text:
                try:
                    src_lang = msg.get("source_lang", "en")
                    if lang == src_lang:
                        translation_text = msg["original"]
                    else:
                        result = run_translation(msg["original"], src_lang, lang)
                        if not result and src_lang != "en" and lang != "en":
                            # Try via English as a pivot
                            to_en = run_translation(msg["original"], src_lang, "en")
                            if to_en:
                                result = run_translation(to_en, "en", lang)
                        translation_text = result or msg["original"]

                    # Persist computed translation for future requests
                    messages_translated.update_one(
                        {"message_id": str(msg["_id"])},
                        {
                            "$set": {f"translations.{lang}": translation_text},
                            "$setOnInsert": {
                                "message_id": str(msg["_id"]),
                                "timestamp": datetime.utcnow(),
                            },
                        },
                        upsert=True,
                    )
                except Exception as e:
                    print(f"On-the-fly translation failed for {msg['_id']}->{lang}: {e}")
                    # Fallback to English if available in stored translations
                    translation_text = translations_map.get("en") or msg["original"]

            results.append({
                "id": str(msg["_id"]),
                "original": msg["original"],
                "translation": translation_text or msg["original"],
                "timestamp": msg["timestamp"].isoformat()
            })
        return {"messages": results}
    except Exception as e:
        print(f"Error in get_messages: {e}")
        return {"error": str(e)}



@app.get("/languages")
def get_languages():
    return {"languages": SUPPORTED_LANGS}


@app.delete("/messages/{message_id}")
def delete_message(message_id: str):
    try:
        raw_result = messages_raw.delete_one({"_id": ObjectId(message_id)})
        trans_result = messages_translated.delete_many({"message_id": message_id})

        if raw_result.deleted_count == 0:
            return {"status": "not_found"}

        return {
            "status": "ok",
            "deleted": {
                "raw": raw_result.deleted_count,
                "translated": trans_result.deleted_count
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/filipino-model")
def get_filipino_model_info():
    """Get current Filipino model and available alternatives"""
    current_model = get_filipino_model()
    return {
        "current_model": current_model,
        "available_models": FILIPINO_ALTERNATIVES,
        "environment_variable": "FILIPINO_MODEL",
        "usage": "Set FILIPINO_MODEL environment variable to switch models (nllb, nllb-large, opus)"
    }

@app.post("/switch-filipino-model")
def switch_filipino_model(model_name: str):
    """Switch Filipino model (requires server restart to take effect)"""
    if model_name.lower() not in FILIPINO_ALTERNATIVES:
        return {"error": f"Invalid model. Available: {list(FILIPINO_ALTERNATIVES.keys())}"}
    
    # This would require server restart to take effect
    return {
        "message": f"Model will be switched to {model_name} on next server restart",
        "new_model": FILIPINO_ALTERNATIVES[model_name.lower()],
        "restart_required": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
