# FashionVerse Backend — Image Upload & Wardrobe Module

FashionVerse is an AI-powered wardrobe management and outfit recommendation platform. This module provides a robust, production-ready, asynchronous image upload and storage system designed to handle user profile pictures and wardrobe items, integrated with our machine learning classification pipeline.

## 🚀 Key Features

- **Asynchronous Execution:** Built on FastAPI, SQLAlchemy 2.0 (async), and `asyncpg` for high-performance PostgreSQL interaction.
- **Storage Isolation Pattern:** All storage operations are abstracted behind a `StorageBackend` interface. The system currently uses local filesystem storage, but can be seamlessly swapped to cloud storage (AWS S3, Azure Blob Storage) without altering API route handlers or service layer logic.
- **Automated Image Processing:** 
  - Offloads CPU-heavy/blocking Pillow resize tasks to worker threads via `anyio.to_thread.run_sync` to prevent blocking the FastAPI async event loop.
  - Automatically generates `150x150` aspect-ratio-preserving thumbnails for all wardrobe uploads.
- **Robust Validations:**
  - File size validation (default max 10MB) via `Content-Length` headers and actual payload checks.
  - MIME-type and extension matching (accepts `.jpg`, `.jpeg`, `.png`, `.webp`).
  - Empty file detection.
- **Global Error Handling:** Custom exceptions (e.g. `FileTooLargeError`, `UnsupportedFileTypeError`) are intercepted globally to return clean, standardized JSON error responses.

---

## 📁 Directory Structure

```text
fashionverse-backend/
├── app/
│   ├── api/
│   │   ├── users.py           # User routes (profile image upload)
│   │   └── wardrobe.py        # Wardrobe routes (item upload with category/notes)
│   ├── database/
│   │   └── connection.py      # Database engine, session maker, and tables initialization
│   ├── models/
│   │   ├── base.py            # Declarative base model
│   │   ├── user.py            # User DB Model (stores profile picture path)
│   │   └── wardrobe.py        # WardrobeItem DB Model (stores metadata, category, and path)
│   ├── schemas/
│   │   ├── user.py            # User-related Pydantic validation schemas
│   │   └── wardrobe.py        # Wardrobe-related Pydantic validation schemas
│   ├── services/
│   │   ├── image_processing.py# Pillow-based operations (thumbnailing, resizing)
│   │   ├── storage_service.py # Storage abstraction and local disk backend
│   │   └── upload_service.py  # Orchestrates validation, storage, DB saving, and processing
│   ├── utils/
│   │   └── exceptions.py      # Standardized upload exception classes
│   ├── config.py              # Application settings, pathing, and constants
│   └── main.py                # App entrypoint, lifespan events, exception handlers
├── uploads/                   # Local storage directory (structured into subfolders)
│   ├── profiles/              # Saved profile pictures
│   ├── wardrobe/              # Main wardrobe photos, structured by category
│   └── thumbnails/            # Scale-down wardrobe items
├── .env                       # Environment configuration file
├── requirements.txt           # Project package dependencies
└── README.md                  # This file
```

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL instance running

### Installation

1. **Clone the repository and enter the directory:**
   ```bash
   cd fashionverse-backend
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your environment:**
   Create a `.env` file in the root directory:
   ```env
   DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>:<port>/<database_name>
   ```

5. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```
   *The database schema will automatically initialize and seed a default test user (`id=1`) upon server startup.*

---

## 🔌 API Endpoints

Once the application is running, you can explore the complete Swagger UI documentation at `http://127.0.0.1:8000/docs`.

### 1. User Registration
Registers a new user and triggers a 6-digit email verification code via SMTP (falls back to console logger if SMTP settings are not set).

* **Endpoint:** `POST /api/v1/auth/register`
* **Content-Type:** `application/json`
* **Request Body:**
  ```json
  {
    "name": "Alice",
    "email": "alice@example.com",
    "password": "securepassword123"
  }
  ```
* **Response (201 Created):**
  ```json
  {
    "id": 3,
    "name": "Alice",
    "email": "alice@example.com",
    "is_verified": false
  }
  ```

---

### 2. Verify Email Address
Validates the 6-digit email OTP verification code.

* **Endpoint:** `POST /api/v1/auth/verify`
* **Content-Type:** `application/json`
* **Request Body:**
  ```json
  {
    "email": "alice@example.com",
    "code": "123456"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Email verified successfully. You can now log in."
  }
  ```

---

### 3. User Login
Validates credentials. If the user's email is not verified, it blocks login and resends a new verification code.

* **Endpoint:** `POST /api/v1/auth/login`
* **Content-Type:** `application/json`
* **Request Body:**
  ```json
  {
    "email": "alice@example.com",
    "password": "securepassword123"
  }
  ```
* **Response (200 OK):**
  ```json
  {
    "access_token": "simulated_token_for_user_3",
    "token_type": "bearer",
    "user": {
      "id": 3,
      "name": "Alice",
      "email": "alice@example.com",
      "is_verified": true
    }
  }
  ```

---

### 4. Upload User Profile Image
Validates and uploads a profile picture, updating the corresponding user's database entry.

* **Endpoint:** `POST /api/v1/users/{user_id}/profile-image`
* **Content-Type:** `multipart/form-data`
* **Parameters:**
  - `user_id` (Path parameter, Integer)
  - `file` (Form file, Binary)
* **Response (201 Created):**
  ```json
  {
    "success": true,
    "message": "Profile image uploaded successfully",
    "image_url": "/uploads/profiles/1/6c593031150c4b07b8d55b4a32ff3f36.jpg",
    "filename": "6c593031150c4b07b8d55b4a32ff3f36.jpg"
  }
  ```

---

### 5. Upload Wardrobe Item
Processes a clothing photo, saves the original image, generates a thumbnail, and adds a metadata entry in the wardrobe.

* **Endpoint:** `POST /api/v1/wardrobe/{user_id}/upload`
* **Content-Type:** `multipart/form-data`
* **Parameters:**
  - `user_id` (Path parameter, Integer)
  - `file` (Form file, Binary)
  - `category` (Form field, String: `top` | `bottom` | `shoes` | `accessories`)
  - `brand` (Form field, String, Optional)
  - `notes` (Form field, String, Optional)
* **Response (201 Created):**
  ```json
  {
    "id": 1,
    "user_id": 1,
    "category": "top",
    "image_path": "wardrobe/1/top/90234f88f6d54efe986b42a61cae4e72.jpg",
    "brand": "TestBrand",
    "notes": "My test shirt",
    "created_at": "2026-07-19T05:00:19.924215"
  }
  ```

---

### 6. Get Daily Outfit Recommendation
Generates a daily outfit suggestion based on items from the user's wardrobe. Uses date-seeded selection to ensure consistency for a single user throughout the day.

* **Endpoint:** `GET /api/v1/outfits/{user_id}/daily`
* **Parameters:**
  - `user_id` (Path parameter, Integer)
* **Response (200 OK):**
  ```json
  {
    "date": "2026-07-19",
    "season": "Summer",
    "top": {
      "id": 1,
      "category": "top",
      "image_path": "wardrobe/1/top/90234f88f6d54efe986b42a61cae4e72.jpg",
      "brand": "TestBrand",
      "notes": "My test shirt"
    },
    "bottom": null,
    "shoes": null,
    "accessories": null,
    "missing_categories": [
      "bottom",
      "shoes"
    ]
  }
  ```

---

## 🧠 Machine Learning Integration

The backend is configured to work alongside our wardrobe classification pipeline located in `app/ml/`:
- **Model Registry:** The models are loaded directly from the `Duvarakesh/FashionVerse` Hugging Face repository.
- **Classification Flow:** Upon uploading a wardrobe item, the image can be classified into categories and sub-categories, detecting colors using KDTree color mapping against CSS3 values.

---

## 🎨 Architectural Decisions

1. **Storage Isolation (Adapter Pattern):** Routes and service classes interact strictly with the `StorageBackend` abstraction. The backend can be migrated to cloud providers simply by implementing the abstract base class and updating the dependency injection configuration in `app/services/storage_service.py`.
2. **Safe Multi-Threading:** Pillow's file operations are CPU-bound and block execution. By calling `anyio.to_thread.run_sync()`, we run these operations in separate worker threads, allowing the FastAPI main thread to continue processing other concurrent requests without lag.
3. **Database Naive UTC Timestamps:** All tables persist UTC timestamps without time zones to match asyncpg expectations, avoiding offset-naive vs. offset-aware exceptions.
4. **Statics Mounting:** Uploaded files are served directly using FastAPI's `StaticFiles` package mounted at `/uploads`, providing a simple way to access assets locally.
