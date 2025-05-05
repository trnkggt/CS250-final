## 📅 Deadline Reminder – CS250 Final Project

This FastAPI-based project integrates with the Canvas LMS to automatically fetch and send deadline reminders to students. It utilizes Celery for asynchronous task execution and Alembic for database migrations.

---

### 🚀 Features

- 🔌 Canvas LMS integration for fetching assignments
- 📤 Asynchronous email/task reminders using Celery
- 🗃️ SQLAlchemy models with Alembic migration support
- 🐳 Dockerized for easy setup and deployment
- 📑 Swagger/OpenAPI docs available at `/docs`

---

### 📁 Project Structure

```
CS250/
├── alembic/                # Alembic migration files
│   └── versions/
├── app/
│   ├── core/               # Core configs
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── celery.py           # Celery app config
│   ├── tasks.py            # Celery background tasks
│   ├── users.py            # User-related configurations
│   └── main.py             # FastAPI entrypoint
├── scripts/                # Helper scripts (e.g., Docker entrypoint)
├── .env.sample             # Sample environment config
├── Dockerfile              # Docker build config
├── docker-compose.yaml     # Docker services config
├── alembic.ini             # Alembic settings
└── pyproject.toml          # Project dependencies and settings
```

---

### ⚙️ Setup Instructions

#### 1. Clone the repository

```bash
git clone https://github.com/your-username/deadline-reminder.git
cd deadline-reminder
```

#### 2. Create and configure environment variables

```bash
cp .env.sample .env
# Fill in required variables (Canvas API token, SMTP credentials, DB URL, etc.)
```

#### 3. Run using Docker

```bash
docker-compose up --build
```

---

### 📄 API Documentation

- Swagger UI: [http://localhost:8080/dev/api/docs](http://localhost:8080/dev/api/docs)
- ReDoc: [http://localhost:8080/redoc](http://localhost:8080/redoc)

---

### ☁️ Tech Stack

- FastAPI
- Celery + Redis (or RabbitMQ)
- Alembic + SQLAlchemy
- Docker + Docker Compose
- Canvas LMS API

---

### 👤 Author

CS250 Final Project – SDSU  
Maintained by Tornike

---