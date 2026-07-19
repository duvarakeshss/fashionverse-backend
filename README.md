# FashionVerse Backend — AI-Powered Wardrobe & Outfit Recommendation Service

FashionVerse is an advanced, production-ready, asynchronous AI wardrobe management and outfit styling platform. Built with FastAPI and SQLAlchemy 2.0, this backend coordinates automated image recognition, dense vector semantic search, Azure Blob Storage cloud orchestration, JWT session authentication, and OpenRouter LLM outfit generation.

---

## 🚀 Key Features

* **Automated ML Classification**: Wardrobe uploads (`POST /wardrobe/{user_id}/upload`) run dynamically through a 5-classifier Keras ML pipeline, automatically predicting the garment's `category` (top/bottom/shoes), `type`, `gender`, `color`, `season`, and `usage`.
* **Natural Language Descriptions**: Constructs a rich semantic description of each clothing item from predicted attributes and brand metadata.
* **Semantic Fashion Search**: Embeds item descriptions into 384-dimensional dense vectors using `SentenceTransformers` ('all-MiniLM-L6-v2') with a high-performance, zero-dependency NumPy projection fallback. Searches wardrobe items semantically using in-memory cosine-similarity scoring.
* **AI Outfit Styling (OpenRouter)**: Invokes OpenRouter LLM (`gpt-oss-120b` / `openai/gpt-4.1` class) on semantic search results to generate custom, natural language outfit recommendations based on the user's wardrobe.
* **Real JWT Authentication & Session Expiry**: Protects endpoints using HTTP Bearer JWT tokens with custom session expiration and PBKDF2-HMAC-SHA256 password hashing.
* **Storage Isolation Pattern**: Abstracted via `StorageBackend` adapter, allowing seamless toggling between local filesystem storage and high-speed Azure Blob Storage cloud backend.
* **Dynamic Public URL Resolution**: Custom Pydantic validators automatically resolve relative image paths to fully qualified, public Azure Blob Storage URLs or local static asset URLs before returning API responses.
* **Safe Multi-Threading**: Pillow image sizing and ML loading tasks run safely inside worker threads via `anyio.to_thread.run_sync` to keep the FastAPI event loop unblocked.

---

## 📁 Directory Structure

```text
fashionverse-backend/
├── app/
│   ├── api/
│   │   ├── auth.py            # Authentication routes (register, verify, login)
│   │   ├── outfits.py         # Outfit recommendation routes
│   │   ├── users.py           # User routes (profile details CRUD & image upload)
│   │   └── wardrobe.py        # Wardrobe routes (upload with ML classification, search, query)
│   ├── database/
│   │   └── connection.py      # Database engine, connection initialization, and user seeding
│   ├── ml/
│   │   ├── models/            # Downloaded Keras classification models (from HuggingFace)
│   │   └── recognition_module.py # ML Keras image classification pipeline
│   ├── models/
│   │   ├── base.py            # Declarative base model class
│   │   ├── user.py            # User SQL Model (profile fields, password hash, profile image)
│   │   └── wardrobe.py        # WardrobeItem SQL Model (classification tags, description, embedding JSON)
│   ├── schemas/
│   │   ├── auth.py            # Authentication request/response validation schemas
│   │   ├── outfit.py          # Outfit validation schemas
│   │   ├── user.py            # User profile request/response schemas (with public URL validator)
│   │   └── wardrobe.py        # Wardrobe item, search, and AI query schemas
│   ├── services/
│   │   ├── auth_service.py    # Registration, login, verification, and JWT session handling
│   │   ├── email_service.py   # Verification email dispatch via SMTP / Console
│   │   ├── embedding_service.py # Dense vector embedding generation (SentenceTransformers/NumPy)
│   │   ├── image_processing.py# Pillow-based operations (thumbnailing, resizing)
│   │   ├── llm_service.py     # OpenRouter AI outfit styling service
│   │   ├── storage_service.py # Storage abstraction (Local & Azure Blob Storage Backends)
│   │   └── upload_service.py  # Coordinates validation, ML pipelines, thumbnails, and uploads
│   ├── utils/
│   │   ├── exceptions.py      # Standardized custom API exceptions
│   │   └── file_utils.py      # Size validations and Pillow-based image checks
│   ├── config.py              # Application settings, environment loader, and startup validation
│   └── main.py                # FastAPI app initialization, middleware, and routers
├── tests/
│   ├── base.py                # BaseTestCase with isolated DB tables and StorageBackend overrides
│   ├── test_auth.py           # Unit tests for registration, verification, login, and JWT logic
│   ├── test_profile.py        # Unit tests for profile details CRUD and profile image uploads
│   └── test_wardrobe.py       # Unit tests for wardrobe upload, semantic search, and AI styling
├── uploads/                   # Local fallback storage directory
├── .env                       # Environment variables config file
├── requirements.txt           # Project dependencies
└── README.md                  # Project documentation (this file)
```

---

## ⚙️ Configuration & Environment

Create a `.env` file in the root directory. The application strictly validates settings at startup and will raise a `ValueError` if required variables are missing:

```env
# Database Settings
DATABASE_URL=postgresql+asyncpg://postgres:1234@localhost:5433/fashionVerse

# JWT Session Security
JWT_ACCESS_SECRET=nestjsPrismaAccessSecret
JWT_REFRESH_SECRET=nestjsPrismaRefreshSecret
JWT_ACCESS_EXPIRATION=24h
JWT_REFRESH_EXPIRATION=7d
JWT_ALGORITHM=HS256

# OpenRouter LLM API
OPENROUTER_API_KEY=sk-or-v1-...

# SMTP Email Configuration (for OTP verification)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=FashionVerse <no-reply@fashionverse.com>

# Azure Blob Storage Configuration (Optional, falls back to local disk if empty)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_BLOB_CONTAINER_NAME=machinemanagerfiles
```

---

## 🛠️ Installation & Setup

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the FastAPI server:**
   ```bash
   uvicorn app.main:app --reload
   ```
   *Note: On startup, the server automatically boots the database schema and seeds a default verified test user (`test@example.com` / `password`).*

---

## 🔌 API Documentation

Explore complete interactive API specs at `http://127.0.0.1:8000/docs`.

### 🔑 Authentication Routes (`/auth`)

#### 1. Register User
* **Endpoint:** `POST /api/v1/auth/register`
* **Request Body:**
  ```json
  {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "password": "securepassword123"
  }
  ```
* **Response (201 Created):** Returns user details with `is_verified: false` and sends a 6-digit OTP code to the email.

#### 2. Verify Email OTP
* **Endpoint:** `POST /api/v1/auth/verify`
* **Request Body:**
  ```json
  {
    "email": "jane@example.com",
    "code": "123456"
  }
  ```

#### 3. Login User
* **Endpoint:** `POST /api/v1/auth/login`
* **Request Body:**
  ```json
  {
    "email": "jane@example.com",
    "password": "securepassword123"
  }
  ```
* **Response (200 OK):** Returns JWT access token and user profile details.

---

### 👤 User Routes (`/users` — Protected by JWT)

#### 1. Get / Update Profile
* **Endpoints:** `GET /api/v1/users/{user_id}/profile` | `POST /api/v1/users/{user_id}/profile`
* **Response (200 OK):** Retrieves or updates user parameters like `shopping_for`, `height`, `budget_range`, `preferred_brands`, etc. The `profile_image` path is automatically resolved to a fully-qualified public storage URL.

#### 2. Upload Profile Image
* **Endpoint:** `POST /api/v1/users/{user_id}/profile-image`
* **Content-Type:** `multipart/form-data`
* **Response (201 Created):** Returns successful upload status along with the public image URL.

---

### 👗 Wardrobe Routes (`/wardrobe` — Protected by JWT)

#### 1. Upload & Auto-Classify Clothing
* **Endpoint:** `POST /api/v1/wardrobe/{user_id}/upload`
* **Content-Type:** `multipart/form-data`
* **Form Fields:** `file` (Binary Image), `brand` (Optional String), `notes` (Optional String)
* **Response (201 Created):** Auto-classifies image and returns predicted clothing category, color, type, generated text description, and the public URL of the uploaded image.

#### 2. Semantic Search
* **Endpoint:** `GET /api/v1/wardrobe/{user_id}/search?q=blue+summer+tshirt&limit=5`
* **Response (200 OK):** Evaluates semantic similarities in-memory and returns items ordered by relevance.

#### 3. AI Outfit Styling Query
* **Endpoint:** `POST /api/v1/wardrobe/{user_id}/query`
* **Request Body:**
  ```json
  {
    "query": "What should I wear for a formal summer dinner party?",
    "limit": 5
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "query": "What should I wear for a formal summer dinner party?",
    "recommendation": "I recommend styling your blue BrandX top with a light blazer...",
    "matched_items": [
      {
        "id": 12,
        "category": "top",
        "image_url": "https://azurestd01.blob.core.windows.net/...",
        "color": "Blue",
        "description": "A blue tshirts for men, suitable for summer in casual occasions. Brand: BrandX.",
        ...
      }
    ]
  }
  ```

---

## 🧪 Testing

We provide a comprehensive, zero-dependency async unit test suite:

```powershell
# Run the complete test suite
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

* **Storage Isolation:** Runs storage logic against a local test uploads directory to protect production folders and cloud storage containers.
* **Database Isolation:** Drops and recreates test tables before each test case, utilising a separate database engine with `NullPool` to prevent concurrency conflicts.
* **Mock Pipelines:** Mocks ML model predictions and OpenRouter LLM HTTP responses to ensure unit tests execute in a few seconds.
