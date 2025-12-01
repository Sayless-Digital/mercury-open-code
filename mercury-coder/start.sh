#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Mercury Coder Startup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on a port
kill_port() {
    local port=$1
    local process_name=$2
    
    if check_port $port; then
        echo -e "${YELLOW}⚠️  $process_name is already running on port $port${NC}"
        echo -e "${YELLOW}   Killing existing process...${NC}"
        
        # Try to kill gracefully first
        lsof -ti :$port | xargs kill -TERM 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if check_port $port; then
            lsof -ti :$port | xargs kill -9 2>/dev/null
            sleep 1
        fi
        
        if check_port $port; then
            echo -e "${RED}✗ Failed to kill process on port $port${NC}"
            return 1
        else
            echo -e "${GREEN}✓ Killed existing $process_name process${NC}"
            return 0
        fi
    else
        echo -e "${GREEN}✓ Port $port is free${NC}"
        return 0
    fi
}

# Function to wait for backend to be ready
wait_for_backend() {
    local max_attempts=30
    local attempt=0
    
    echo -e "${BLUE}⏳ Waiting for backend to be ready...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend is ready!${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
        echo -n "."
    done
    
    echo ""
    echo -e "${RED}✗ Backend failed to start within ${max_attempts} seconds${NC}"
    return 1
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down...${NC}"
    
    # Kill OpenCode backend
    if check_port 4096; then
        echo -e "${YELLOW}   Stopping OpenCode backend...${NC}"
        lsof -ti :4096 | xargs kill -TERM 2>/dev/null
        sleep 1
        lsof -ti :4096 | xargs kill -9 2>/dev/null
    fi
    
    # Kill frontend
    if check_port 5173; then
        echo -e "${YELLOW}   Stopping frontend...${NC}"
        lsof -ti :5173 | xargs kill -TERM 2>/dev/null
        sleep 1
        lsof -ti :5173 | xargs kill -9 2>/dev/null
    fi
    
    # Kill Electron processes
    echo -e "${YELLOW}   Stopping Electron...${NC}"
    pkill -f electron 2>/dev/null
    sleep 1
    
    echo -e "${GREEN}✓ All processes stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load nvm if available
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    echo -e "${BLUE}Loading nvm...${NC}"
    source "$HOME/.nvm/nvm.sh"
    echo -e "${GREEN}✓ nvm loaded (Node $(node --version))${NC}"
elif [ -s "$HOME/.config/nvm/nvm.sh" ]; then
    echo -e "${BLUE}Loading nvm...${NC}"
    source "$HOME/.config/nvm/nvm.sh"
    echo -e "${GREEN}✓ nvm loaded (Node $(node --version))${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: nvm not found, trying system node/npm${NC}"
fi

# Verify npm is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ Error: npm not found${NC}"
    echo -e "${YELLOW}   Please install Node.js or ensure nvm is properly configured${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 1: Checking existing processes...${NC}"
echo ""

# Check and kill OpenCode backend if running
kill_port 4096 "OpenCode Backend"

# Check and kill frontend if running
kill_port 5173 "Frontend (Vite dev server)"

echo ""
echo -e "${BLUE}Step 2: Starting OpenCode backend...${NC}"
echo ""

# Check if bun is installed
if ! command -v bun &> /dev/null; then
    echo -e "${RED}✗ Error: bun not found${NC}"
    echo -e "${YELLOW}   Please install bun: curl -fsSL https://bun.sh/install | bash${NC}"
    exit 1
fi

# Start OpenCode backend from opencode-backend directory
cd ../opencode-backend
if [ ! -d "packages/opencode" ]; then
    echo -e "${RED}✗ Error: opencode-backend/packages/opencode not found${NC}"
    echo -e "${YELLOW}   Please ensure opencode-backend is properly checked out${NC}"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing OpenCode backend dependencies...${NC}"
    bun install
fi

# Start OpenCode backend in background
echo -e "${GREEN}✓ Starting OpenCode backend server on port 4096...${NC}"
bun run --cwd packages/opencode --conditions=browser src/index.ts serve --port 4096 --hostname 127.0.0.1 --print-logs --log-level DEBUG > ../mercury-coder/opencode-backend.log 2>&1 &
BACKEND_PID=$!
cd ../mercury-coder

echo -e "${GREEN}✓ OpenCode backend process started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo -e "${BLUE}⏳ Waiting for OpenCode backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://127.0.0.1:4096/config > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OpenCode backend is ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

echo ""
echo -e "${BLUE}Step 3: Starting frontend (Vite)...${NC}"
echo ""

# Start frontend (Vite)
echo -e "${GREEN}✓ Starting Vite dev server...${NC}"
npm run dev:vite > frontend.log 2>&1 &
FRONTEND_PID=$!

echo -e "${GREEN}✓ Frontend (Vite) process started (PID: $FRONTEND_PID)${NC}"

# Wait for Vite to be ready
echo -e "${BLUE}⏳ Waiting for Vite dev server to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Vite dev server is ready!${NC}"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

echo ""
echo -e "${BLUE}Step 4: Starting Electron desktop app...${NC}"
echo ""

# Start Electron with NODE_ENV set
NODE_ENV=development npm run dev:electron > electron.log 2>&1 &
ELECTRON_PID=$!

echo -e "${GREEN}✓ Electron process started (PID: $ELECTRON_PID)${NC}"
echo ""

sleep 2

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ All services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "OpenCode Backend: ${BLUE}http://127.0.0.1:4096${NC}"
echo -e "Frontend:         ${BLUE}http://localhost:5173${NC}"
echo -e "Electron:         ${BLUE}Desktop app window should be open${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for user interrupt
wait


