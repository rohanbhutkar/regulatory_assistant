# Clinical Knowledge Agent Platform

AI-Powered Clinical Research Platform with multi-agent architecture for pharmaceutical research and development.

## Features

### Persona-Based Access
- **Asset Management**: Portfolio oversight, cost analysis, and revenue projection
- **Study Designer**: Protocol authoring, trial design, and site selection
- **Commercial**: Market analysis, revenue modeling, and payer insights

### Core Capabilities
- 15+ specialized AI agents (Clinical Trials, PubMed, AACT, OpenFDA, Simulation, etc.)
- Real-time research agent chat with markdown support
- Interactive data visualizations and analytics
- WebSocket-based progress tracking
- Comprehensive data integration (80K+ trials, 2.9M+ claims records)

## Tech Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS v4
- **UI Components**: Radix UI + shadcn/ui
- **Charts**: Recharts
- **State Management**: React Hooks + SWR

### Backend (Planned Integration)
- **Framework**: Python FastAPI
- **AI/ML**: LangChain + LangGraph
- **Data Processing**: Pandas, NumPy
- **WebSocket**: FastAPI WebSocket support

## Getting Started

### Prerequisites
- Node.js 18+ and pnpm
- Python 3.9+ (for backend)

### Installation

1. **Install frontend dependencies:**
\`\`\`bash
pnpm install
\`\`\`

2. **Run development server:**
\`\`\`bash
pnpm dev
\`\`\`

3. **Open your browser:**
Navigate to [http://localhost:3000](http://localhost:3000)

### Backend Setup (Optional)

The frontend currently uses mock data. To connect to the backend:

1. **Set environment variables:**
\`\`\`bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=ws://localhost:8001/ws
\`\`\`

2. **Start the FastAPI backend:**
\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
\`\`\`

## Project Structure

\`\`\`
clinical-knowledge-platform/
├── app/                          # Next.js app router pages
│   ├── page.tsx                 # Persona gateway (landing page)
│   ├── asset-management/        # Asset management dashboard
│   ├── study-designer/          # Study designer workspace
│   ├── commercial/              # Commercial simulation
│   └── research/                # Research agent chat
├── components/                   # React components
│   ├── asset-management/        # Asset-specific components
│   ├── chat/                    # Chat interface components
│   ├── commercial/              # Commercial simulation components
│   ├── layout/                  # Layout components (header, footer)
│   ├── persona-gateway/         # Persona selection components
│   ├── study-designer/          # Study designer components
│   └── ui/                      # Reusable UI components (shadcn)
├── lib/                         # Utilities and configurations
│   ├── api/                     # API client and WebSocket
│   ├── data/                    # Mock data
│   ├── hooks/                   # Custom React hooks
│   └── types/                   # TypeScript type definitions
└── public/                      # Static assets
\`\`\`

## Key Features by Persona

### Asset Management
- Portfolio overview with key metrics
- Asset table with expandable trial details
- Cost breakdown and revenue projections
- Risk assessment and ROI analysis
- Interactive charts and visualizations

### Study Designer
- Study list and file explorer
- Reference trials selection (80K+ trials)
- IE Criteria Optimizer with population funnel
- Site selection with geographic analysis
- Protocol authoring workspace
- Trial simulation and budget calculator

### Commercial
- Revenue simulator with adjustable parameters
- Quarterly revenue projections
- Patient funnel analysis
- Sensitivity analysis
- Market penetration modeling
- Payer coverage assumptions

## Data Sources

The platform integrates with multiple data sources:
- **TrialTrove**: 80K+ clinical trials
- **SiteTrove**: Global site database
- **Claims Data**: 2.9M+ patient records
- **Payer Data**: 50+ CSV files with market data
- **PubMed**: Medical literature
- **OpenFDA**: FDA drug data

## API Integration

### WebSocket Connection
\`\`\`typescript
import { useWebSocket } from '@/lib/hooks/use-websocket'

const { isConnected, lastMessage, sendMessage } = useWebSocket('ws://localhost:8001/ws')
\`\`\`

### REST API Calls
\`\`\`typescript
import { apiClient } from '@/lib/api/client'

const assets = await apiClient.getAssets()
const simulation = await apiClient.runRevenueSimulation(params)
\`\`\`

## Development

### Adding a New Persona
1. Add persona definition to `lib/data/personas.ts`
2. Create persona page in `app/[persona-id]/page.tsx`
3. Build persona-specific components in `components/[persona-id]/`
4. Add types to `lib/types/[persona-id]-types.ts`

### Adding a New Agent
1. Define agent in `lib/data/agents.ts`
2. Update agent selector in `components/chat/agent-selector.tsx`
3. Implement backend agent logic (FastAPI)

## Deployment

### Vercel Deployment
\`\`\`bash
pnpm build
vercel deploy
\`\`\`

### Environment Variables
\`\`\`bash
NEXT_PUBLIC_API_URL=https://your-api.com
NEXT_PUBLIC_WS_URL=wss://your-api.com/ws
\`\`\`

## Contributing

This is a demo application showcasing the Clinical Knowledge Agent Platform architecture. For production use, connect to the FastAPI backend with real data sources.

## License

Proprietary - Clinical Research Platform Demo
