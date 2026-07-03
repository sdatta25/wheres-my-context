# Where's My Context — API Reference

## Overview
The API provides endpoints for memory management, knowledge graph operations, and context recall.

## Base URL
`http://localhost:8000/api`

## Authentication
For Cognee Cloud: Include headers:
- `X-Api-Key`: Your Cognee Cloud API key
- `X-Tenant-Id`: Your Cognee Cloud tenant ID

## Endpoints

### Memory Operations

#### Add Memory
```
POST /memories
Content-Type: application/json

{
  "text": "We decided to use PostgreSQL for the main database",
  "type": "decision",
  "project": "backend",
  "author": "Alice"
}
```

**Response:**
```json
{
  "memory": {
    "id": "mem_123",
    "text": "We decided to use PostgreSQL...",
    "type": "decision",
    "project": "backend",
    "author": "Alice",
    "created_at": "2026-07-02T10:30:00Z",
    "concepts": ["PostgreSQL", "database", "decision"]
  }
}
```

#### List Memories
```
GET /memories?project=backend
```

#### Delete Memory
```
DELETE /memories/{memory_id}
```

### Knowledge Graph

#### Get Graph
```
GET /graph?project=backend
```

### Search & Recall

#### Search
```
POST /search
{
  "query": "Why did we pick PostgreSQL?",
  "project": "backend"
}
```

#### Recall Context
```
POST /recall
{
  "project": "backend",
  "task": "Set up new database connection"
}
```

### System

#### Status
```
GET /status
```

#### Reseed Demo Data
```
POST /seed
```

#### Reset Project
```
POST /reset?project=backend
```

## Error Handling

All errors return:
```json
{
  "detail": "Error message here"
}
```

**Status Codes:**
- `200 OK` — Success
- `400 Bad Request` — Invalid input
- `404 Not Found` — Not found
- `500 Internal Server Error` — Server error
