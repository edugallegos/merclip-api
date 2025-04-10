# FastAPI Template

This is a template repository for building APIs using FastAPI. It provides a clean, well-structured starting point for your API projects.

## Features

- FastAPI framework for high-performance API development
- Pydantic models for data validation
- Example router demonstrating CRUD operations
- Basic logging setup
- Docker support
- Testing setup with pytest

## Project Structure

```
.
├── app/
│   ├── main.py              # Main application file
│   ├── routers/             # API route handlers
│   │   └── example.py       # Example router
│   └── services/            # Business logic and services
├── tests/                   # Test files
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker Compose configuration
```

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

Once the server is running, you can access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Endpoints

The template includes example endpoints at `/example`:
- GET `/example` - List all items
- GET `/example/{item_id}` - Get a specific item
- POST `/example` - Create a new item

## Testing

Run tests with:
```bash
pytest
```

## Docker Support

Build and run with Docker:
```bash
docker-compose up --build
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 