# Clinical Knowledge Agent Platform

A comprehensive, persona-based clinical research platform with AI-powered insights and advanced analytics.

## Features

### 🎯 Persona-Based Access
- **Asset Management**: Portfolio oversight and investment tracking
- **Study Designer**: Protocol design and trial planning  
- **Commercial**: Market analysis and revenue modeling

### 🚀 Key Capabilities
- Real-time data processing from local CSV files
- AI-powered insights using existing agents
- Interactive visualizations and simulations
- Seamless persona switching with context preservation
- Complete workflows from data input to actionable insights

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- npm

### Environment Variables

The backend requires several API keys and credentials to function properly. Create a `.env` file in the `backend` directory with the following variables:

```env
# LLM Configuration (Required)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# BioOntology API (Optional - for medical ontology queries)
BIOONTOLOGY_API_KEY=your_bioontology_api_key_here

# OpenFDA API (Optional - for FDA data)
OPENFDA_API_KEY=your_openfda_api_key_here

# Google Custom Search API (Optional - for literature searches)
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here

# AACT Database Configuration (Optional - for clinical trials data)
AACT_DB_USERNAME=your_aact_username
AACT_DB_PASSWORD=your_aact_password

# Redis Configuration (Optional - defaults to localhost:6379)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

**For Docker/Kubernetes deployments**, these should be provided as environment variables via secrets or ConfigMaps.

**Getting API Keys:**
- **Anthropic API**: https://console.anthropic.com/
- **BioOntology**: https://bioportal.bioontology.org/
- **OpenFDA**: https://open.fda.gov/apis/authentication/
- **Google Custom Search**: https://developers.google.com/custom-search/v1/introduction
- **AACT Database**: https://aact.ctti-clinicaltrials.org/connect

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repository-url>
   cd study_designer
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   ```

4. **Configuration**:
   - Create a `backend/.env` file with your API keys (see Environment Variables section above)
   - The `backend/config.py` is already included and reads from environment variables

### Running the Application

#### Option 1: Using Docker (Recommended for Production)
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Option 2: Using the Start Script
```bash
./start.sh
```

#### Option 3: Manual Start

**Terminal 1 - Backend**:
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main_complete.py
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

### Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- API Documentation: http://localhost:8001/docs

## Architecture

### Backend (Python FastAPI)
- **Data Loading**: Optimized CSV data loading with caching
- **API Routes**: RESTful endpoints for all personas
- **WebSocket**: Real-time communication for progress tracking
- **Agent Integration**: Leverages existing 15+ specialized agents

### Frontend (React/Next.js)
- **Persona Gateway**: Role-based landing page
- **Asset Management**: Portfolio overview with drill-down capabilities
- **Study Designer**: Trial design workspace with tabbed interface
- **Commercial**: Revenue simulation and market analysis tools

### Data Sources
- TrialTrove: Clinical trial data
- SiteTrove: Site performance data
- Claims Data: Patient population analysis
- Payer Data: Market and coverage analysis
- FDA Labels: Regulatory information

## Personas

### Asset Management
- Portfolio overview with cost analysis
- Revenue projections and risk assessment
- Asset drill-down with trial details
- Bulk operations and cohort analytics

### Study Designer
- Trial file explorer with filtering
- Protocol design workspace
- Reference trials management
- IE criteria optimization
- Site selection with map visualization
- Study startup simulation
- Budget calculation tools

### Commercial
- Revenue curve simulation engine
- Market analysis and competitive landscape
- Patient funnel simulation
- Payer analysis and coverage trends
- Scenario planning and sensitivity analysis

## Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main_complete.py
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

The backend will run on port 8001 and the frontend on port 3000.

## Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Container Architecture
- **Backend Container**: Python 3.12-slim with FastAPI
- **Frontend Container**: Node 18-alpine with Next.js
- **Networking**: Bridge network for inter-service communication
- **Health Checks**: Automatic health monitoring for both services

### Building Images
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend
docker-compose build frontend
```

### Managing Services
```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v
```

### Environment Configuration

For Docker deployments, you can provide environment variables in multiple ways:

**Option 1: Environment file**
Create a `backend/.env` file with your API keys (see Environment Variables section above).

**Option 2: Docker Compose environment section**
Add environment variables directly in `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - ANTHROPIC_API_KEY=your_api_key_here
      - BIOONTOLOGY_API_KEY=your_key_here
      # Add other variables as needed
```

**Option 3: Kubernetes Secrets** (for production)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:
  anthropic-api-key: your_anthropic_api_key_here
  bioontology-api-key: your_bioontology_api_key_here
  # Add other secrets as needed
```

Then reference in your deployment:
```yaml
env:
  - name: ANTHROPIC_API_KEY
    valueFrom:
      secretKeyRef:
        name: api-secrets
        key: anthropic-api-key
```

### Volume Mounts
- Backend logs are persisted to `./backend/logs`
- Data directory can be mounted (currently commented out in docker-compose.yml)

## Local Demo Features

- **Single-machine deployment** - Everything runs locally
- **Fast startup** - Optimized data loading and caching
- **Complete workflows** - All personas fully functional
- **Real data** - Uses existing CSV files as-is
- **Existing agents** - Leverages all 15+ existing agents

## API Endpoints

### Personas
- `GET /api/personas/` - Get available personas
- `GET /api/personas/{id}/dashboard` - Get persona dashboard
- `GET /api/personas/{id}/permissions` - Get persona permissions

### Assets
- `GET /api/assets/` - Get asset portfolio
- `GET /api/assets/{id}` - Get asset details
- `GET /api/assets/portfolio/summary` - Get portfolio summary

### Trials
- `GET /api/trials/` - Get trials list
- `GET /api/trials/{id}` - Get trial details
- `POST /api/trials/` - Create new trial
- `POST /api/trials/{id}/startup-simulation` - Run simulation

### Commercial
- `POST /api/commercial/revenue-simulation` - Run revenue simulation
- `POST /api/commercial/scenario-analysis` - Run scenario analysis
- `POST /api/commercial/patient-funnel-simulation` - Simulate patient funnel

### Data
- `GET /api/data/trialtrove` - Get TrialTrove data
- `GET /api/data/sitetrove` - Get SiteTrove data
- `POST /api/data/claims/population-analysis` - Analyze population
- `GET /api/data/payer` - Get payer data

## WebSocket Communication

Real-time updates for:
- Query processing progress
- Simulation progress
- Agent status updates
- Live collaboration features

## Contributing

This platform builds upon the existing Clinical Knowledge Agent foundation while adding persona-based architecture and advanced analytics capabilities.

## License

Internal use only - Clinical Knowledge Agent Platform













