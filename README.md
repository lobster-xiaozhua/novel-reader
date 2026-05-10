# Novel Reader

A novel reader application with FastAPI backend and Vue 3 frontend.

## Features

- FastAPI backend with async support
- Vue 3 frontend with modern UI
- Docker deployment ready
- Comprehensive test coverage
- **Adaptive code update system** - update project code via natural language instructions

## Quick Start

```bash
docker-compose up
```

Or use the one-click start script:

```bash
# Linux / macOS / WSL
./start.sh

# Windows PowerShell
.\start.ps1
```

## Code Update Tool

This project supports updating code through natural language instructions.

### CLI Usage

```bash
# View project structure
python update.py --structure

# Preview update plan (no execution)
python update.py --plan "add model Comment"

# Execute update
python update.py "add model Comment"
python update.py "add API review"
python update.py "add dependency requests, numpy"

# View update history
python update.py --history

# Rollback last update
python update.py --rollback
```

### Supported Instructions

| Instruction | Description | Example |
|------------|-------------|---------|
| Add Model | Create new data model | `add model Comment` |
| Add API | Create new API routes | `add API review` |
| Add Route | Add new router module | `add route bookmark` |
| Update Config | Modify configuration | `update config` |
| Add Dependency | Add Python packages | `add dependency requests` |
| Fix | Scan and fix code issues | `fix TODO items` |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/update/execute` | Execute update instruction |
| POST | `/api/update/plan` | Preview update plan |
| GET | `/api/update/history` | Get update history |
| POST | `/api/update/rollback` | Rollback last update |
| GET | `/api/update/structure` | Detect project structure |

### Features

- **Auto-detect project structure** - Automatically identifies backend framework (FastAPI/Flask/Django) and frontend framework (Vue/React/Angular)
- **Smart code generation** - Generates code templates based on project type
- **Automatic backup** - Backs up files before updating, supports rollback
- **Update history** - Records all update operations for traceability
- **Safe rollback** - One-click rollback to previous version

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## License

MIT
