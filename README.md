# 🚗 Let-Me-Go Backend

This is the backend service for the **Vehicle Finder** application — a system designed to help people report vehicles found with issues (like headlights left on, flat tires, etc.) and notify their respective owners.

---

## 🧐 What is this?

When someone notices a vehicle in a parking lot or on the road with a potential issue (e.g., lights left on, leaking fluids, etc.), they can report it through this application. The backend processes the report and notifies the vehicle owner if the vehicle is registered in the system.

---

## 🛠️ Tech Stack

- **Framework**: \[FastAPI]
- **Database**: \[PostgreSQL]
- **Docker**: Containerized setup for development and production

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/aswanthabam/vehicle-finder-backend.git
cd vehicle-finder-backend
```

### 2. Create Environment Configuration

Copy the example `.env` file and update it with your credentials:

```bash
cp .env.example .env
```

Edit the `.env` file with the appropriate values (e.g., database URL, secret keys, etc.).

### 3. Run the App with Docker

Start the backend services using Docker Compose:

```bash
docker compose up -d
```

The backend should now be up and running on the configured port (default: `http://localhost:8000` depending on env configuration).

---

## 📬 API Documentation

Once the server is running, visit:

- **Swagger/OpenAPI Docs**: `http://localhost:8000/docs`
- **Redoc**: `http://localhost:8000/redoc`

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---
