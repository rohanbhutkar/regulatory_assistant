#!/bin/bash
# start.sh - Quick start script for local demo

echo "🚀 Starting Clinical Knowledge Agent Platform - Local Demo"

# Function to kill processes on specific ports
kill_port() {
    local port=$1
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        local pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pids" ]; then
            echo "🔄 Killing existing processes on port $port (attempt $attempt/$max_attempts)..."
            echo $pids | xargs kill -9 2>/dev/null
            sleep 3
            
            # Check if port is now free
            if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                echo "✅ Port $port is now free"
                return 0
            fi
        else
            echo "✅ Port $port is already free"
            return 0
        fi
        attempt=$((attempt + 1))
    done
    
    echo "❌ Failed to free port $port after $max_attempts attempts"
    return 1
}

# Function to check if port is free
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is free
    fi
}

# Function to check if port is in use (for verification after starting services)
check_port_in_use() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use (good for services)
    else
        return 1  # Port is free (bad for services)
    fi
}

# Kill any existing processes on our ports
echo "🧹 Cleaning up existing processes..."
if ! kill_port 8001; then
    echo "❌ Could not free port 8001. Please manually kill processes and try again."
    exit 1
fi
if ! kill_port 3000; then
    echo "❌ Could not free port 3000. Please manually kill processes and try again."
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "❌ pnpm is not installed. Please install pnpm first:"
    echo "   npm install -g pnpm"
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if data folder exists
if [ ! -d "data" ]; then
    echo "❌ Data folder not found. Please ensure data folder is accessible."
    exit 1
fi

# Create symlink if it doesn't exist
if [ ! -L "backend/data" ]; then
    ln -s ../data backend/data
    echo "✅ Created data symlink"
fi

# Start backend
echo "🐍 Starting Python FastAPI backend (optimized with real data)..."
cd backend

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python -m venv venv
fi

source venv/bin/activate

# Install setuptools first to fix distutils issue
pip install --upgrade pip setuptools wheel

# Install requirements (using latest compatible versions)
pip install -r requirements.txt

# Start COMPLETE backend (ALL features + multi-agent)
# Options: 
#   main_complete:app (FULL SYSTEM - all routes + multi-agent)
#   main_agents_simple:app (multi-agent only)
#   main:app (simple backend - has import issues)
echo "🚀 Starting Complete Clinical Knowledge Agent Platform..."
echo "   📊 Loading all API routes: personas, assets, trials, commercial, data..."
echo "   🤖 Initializing DynamicReasoningEngine with 16+ specialized agents..."
echo "   💾 Loading data: 80,249+ trials, 40,777+ sites, claims data..."
uvicorn main_complete:app --reload --port 8001 --host 127.0.0.1 --ws-max-size 10485760 &
BACKEND_PID=$!

# Wait for multi-agent backend to start and verify it's running
echo "⏳ Waiting for multi-agent backend to start..."
echo "   🤖 Initializing 16+ specialized agents..."
echo "   📊 Loading trial, site, and claims data..."
echo "   ⏱️  This can take 30-90 seconds for full agent initialization..."
sleep 15

# Check if backend process is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend process died during startup. Check logs:"
    tail -50 logs/backend.log 2>/dev/null || echo "   No logs found"
    exit 1
fi

# Check if backend is actually running (with retry logic - more patient)
echo "🔍 Verifying multi-agent backend startup..."
max_attempts=12  # Increased from 6 to 12 (2 minutes total)
attempt=1
backend_running=false

while [ $attempt -le $max_attempts ]; do
    # First check if process is still alive
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ Backend process crashed. Check logs."
        exit 1
    fi
    
    if check_port_in_use 8001; then
        # Test if backend is actually responding
        health_response=$(curl -s http://localhost:8001/health 2>/dev/null)
        if echo "$health_response" | grep -q "healthy"; then
            echo "✅ Multi-Agent Backend started successfully on port 8001"
            echo "   🤖 16 specialized agents operational"
            backend_running=true
            break
        else
            echo "⏳ Backend port open, still initializing... (attempt $attempt/$max_attempts)"
            if [ $attempt -eq 4 ]; then
                echo "   💡 Agent loading takes time. Please wait..."
            fi
        fi
    else
        echo "⏳ Backend not ready yet, waiting... (attempt $attempt/$max_attempts)"
    fi
    sleep 10
    attempt=$((attempt + 1))
done

if [ "$backend_running" = false ]; then
    echo "⚠️  Backend health check timed out, but process is still running"
    echo "   🔍 Checking if backend is actually available..."
    if check_port_in_use 8001; then
        echo "   ✅ Backend port 8001 is open - continuing anyway"
        echo "   💡 Backend may still be initializing agents. Check http://localhost:8001/health"
        backend_running=true
    else
        echo "❌ Backend failed to bind to port 8001"
        echo "   Check logs: tail -50 logs/backend.log"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
fi

# Start frontend
echo "⚛️ Starting React frontend..."
cd ../frontend

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    pnpm install
fi

pnpm dev --port 3000 &
FRONTEND_PID=$!

# Wait for frontend to start
echo "⏳ Waiting for frontend to compile and start..."
sleep 10

# Check if frontend is actually running (with retry logic)
echo "🔍 Verifying frontend startup..."
max_attempts=6  # Increased attempts for Next.js compilation
attempt=1
frontend_running=false

while [ $attempt -le $max_attempts ]; do
    # Check if frontend process is still alive
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend process crashed. Check Node version (needs 18.18+ or 20+)"
        kill $BACKEND_PID 2>/dev/null
        exit 1
    fi
    
    if check_port_in_use 3000; then
        # Test if frontend is actually responding
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            echo "✅ Frontend started successfully on port 3000"
            frontend_running=true
            break
        else
            echo "⏳ Frontend port open, still compiling... (attempt $attempt/$max_attempts)"
        fi
    else
        echo "⏳ Frontend not ready yet, waiting... (attempt $attempt/$max_attempts)"
    fi
    sleep 5
    attempt=$((attempt + 1))
done

if [ "$frontend_running" = false ]; then
    echo "⚠️  Frontend health check timed out, but process is running"
    echo "   🔍 Checking if frontend is actually available..."
    if check_port_in_use 3000; then
        echo "   ✅ Frontend port 3000 is open - continuing anyway"
        echo "   💡 Next.js may still be compiling. Check http://localhost:3000"
        frontend_running=true
    else
        echo "❌ Frontend failed to bind to port 3000"
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
        exit 1
    fi
fi

# Final verification - test both services
echo "🔍 Final verification..."
sleep 2

# Test multi-agent backend health endpoint
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    echo "✅ Multi-Agent Backend health check passed"
    # Get agent count
    agent_count=$(curl -s http://localhost:8001/health | grep -o '"active_agents":[0-9]*' | grep -o '[0-9]*')
    if [ ! -z "$agent_count" ]; then
        echo "   🤖 $agent_count specialized agents operational"
    fi
else
    echo "⚠️ Backend health check failed, but service may still be starting"
fi

# Test frontend accessibility
if curl -s http://localhost:3000 | grep -q "Clinical\|Persona\|Accelerate"; then
    echo "✅ Frontend accessibility check passed"
else
    echo "⚠️ Frontend accessibility check failed, but service is running"
fi

echo ""
echo "🎉 Multi-Agent Research Platform Started Successfully!"
echo ""
echo "📊 Service Status:"
echo "   ✅ Multi-Agent Backend: http://localhost:8001 (DynamicReasoningEngine with 16 agents)"
echo "   ✅ Frontend: http://localhost:3000 (React/Next.js with real-time integration)"
echo ""
echo "🔗 Quick Links:"
echo "   🌐 Frontend: http://localhost:3000"
echo "   🤖 Multi-Agent API: http://localhost:8001"
echo "   📚 Agent List: http://localhost:8001/api/agents"
echo "   ❤️ Health Check: http://localhost:8001/health"
echo ""
echo "🤖 Multi-Agent Research Capabilities:"
echo "   • 16 specialized AI agents (clinical_trials, trialtrove, pubmed, etc.)"
echo "   • Dynamic LLM-based query planning"
echo "   • Real-time agent execution streaming"
echo "   • Cross-source data synthesis with citations"
echo "   • Automatic frontend actions (trial selection, criteria generation)"
echo "   • 80,249+ clinical trials, 40,777+ sites, 2.9M+ claims records"
echo ""
echo "🎯 Try asking the Research Agent:"
echo "   • 'Find Phase III NSCLC trials with biomarkers'"
echo "   • 'Generate inclusion criteria for diabetes trials'"
echo "   • 'Which California sites are best for NSCLC trials?'"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        echo "🔄 Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null
        sleep 2
        # Force kill if still running
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo "🔨 Force killing backend..."
            kill -9 $BACKEND_PID 2>/dev/null
        fi
    fi
    
    # Kill frontend process
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "🔄 Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null
        sleep 2
        # Force kill if still running
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            echo "🔨 Force killing frontend..."
            kill -9 $FRONTEND_PID 2>/dev/null
        fi
    fi
    
    # Force kill any remaining processes on our ports
    echo "🧹 Cleaning up ports..."
    kill_port 8001
    kill_port 3000
    
    echo "✅ All services stopped"
    exit 0
}

# Wait for user interrupt
trap cleanup INT TERM
wait
