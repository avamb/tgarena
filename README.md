# TG-Ticket-Agent

Multi-agent Telegram bot for selling event tickets via Bill24/TixGear platform.

## Overview

TG-Ticket-Agent allows users to purchase event tickets through Telegram. The system:

- Supports multiple ticket agents, each with their own deep link
- Integrates with Bill24/TixGear API for event data and ticket management
- Uses a modified Bill24 widget as Telegram WebApp for seat selection
- Delivers tickets with QR codes directly in Telegram
- Includes an admin panel for management

## Technology Stack

### Backend
- **Runtime**: Python 3.11+
- **Bot Framework**: aiogram 3.x
- **API Framework**: FastAPI
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0 + Alembic
- **Task Queue**: Redis + arq

### Frontend (Admin Panel)
- **Framework**: React 18
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **State**: React Query + Zustand

### Widget
- **Framework**: AngularJS 1.5.8 (modified Bill24 widget)
- **Key Change**: Telegram Chat-ID authentication instead of email

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (optional)

### Development Setup

1. **Clone and setup:**
   ```bash
   git clone <repository>
   cd TG-Ticket-Agent
   ./init.sh
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start with Docker (recommended):**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

   Or start services manually:
   ```bash
   # Terminal 1 - Backend API
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --reload --port 8000

   # Terminal 2 - Bot
   cd backend
   source venv/bin/activate
   python -m bot.main

   # Terminal 3 - Admin Panel
   cd admin
   npm run dev
   ```

4. **Access:**
   - Admin Panel: http://localhost:5173
   - API Docs: http://localhost:8000/api/docs
   - Bot: Telegram @YourBotUsername

## Project Structure

```
TG-Ticket-Agent/
├── backend/                 # Python backend
│   ├── app/
│   │   ├── api/            # FastAPI routes
│   │   ├── core/           # Config, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Helpers
│   ├── migrations/         # Alembic migrations
│   └── tests/              # Tests
├── bot/                    # Telegram bot
│   ├── handlers/           # Message handlers
│   ├── keyboards/          # Inline keyboards
│   ├── middlewares/        # Bot middlewares
│   ├── locales/            # i18n JSON files
│   └── main.py             # Entry point
├── admin/                  # React admin panel
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── store/          # Zustand stores
│   │   └── hooks/          # Custom hooks
│   └── package.json
├── widget/                 # Modified Bill24 widget
│   ├── scripts/
│   ├── templates/
│   └── styles/
├── docker-compose.yml      # Production compose
├── docker-compose.dev.yml  # Development compose
├── Dockerfile              # Backend Dockerfile
├── init.sh                 # Setup script
└── README.md
```

## Configuration

Key environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `ADMIN_JWT_SECRET` | Secret for JWT tokens | Yes |
| `BILL24_TEST_URL` | Bill24 test API endpoint | No |
| `BILL24_REAL_URL` | Bill24 production API endpoint | No |

See `.env.example` for all options.

## Deployment (Dokploy)

The project is configured for Dokploy deployment:

```bash
docker-compose up --build -d
```

The application exposes port 3000 (configurable via `PORT` env var).

Health check: `GET /api/health`

## User Flows

### Telegram User
1. Click agent deep link (`t.me/Bot?start=agent_123`)
2. Browse events in Telegram
3. Click "Buy Ticket" to open WebApp
4. Select seats and complete payment
5. Receive tickets with QR codes in Telegram

### Admin
1. Login to admin panel
2. Create and manage agents
3. View users, orders, tickets
4. Configure webhooks for integrations

## Bill24 API Integration

The system integrates with Bill24/TixGear API:

- **GET_ALL_ACTIONS** - Fetch events
- **CREATE_USER** - Register Telegram users
- **RESERVATION** - Reserve seats
- **CREATE_ORDER** - Create purchase order
- **GET_TICKETS_BY_ORDER** - Retrieve tickets

## Localization

Supports Russian (default) and English:
- Bot messages: `bot/locales/{lang}.json`
- Admin panel: English

## License

Proprietary - All rights reserved

## Contact

For support or questions, contact the development team.
