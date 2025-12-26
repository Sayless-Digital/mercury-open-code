#!/bin/bash

# Colors for output
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Mercury OpenCode Development Setup${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""

# Check if dependencies are installed
echo -e "${YELLOW}Checking dependencies...${NC}"

# Check for Bun
if ! command -v bun &> /dev/null; then
    echo -e "${YELLOW}Warning: Bun is not installed. Backend may not start properly.${NC}"
    echo "Install from: https://bun.sh"
else
    echo -e "${GREEN}✓ Bun found${NC}"
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: Node.js is not installed. Frontend may not start properly.${NC}"
else
    echo -e "${GREEN}✓ Node.js found${NC}"
fi

# Check for Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Warning: Python3 is not installed. Whisper backend may not start.${NC}"
else
    echo -e "${GREEN}✓ Python3 found${NC}"
fi

echo ""
echo -e "${GREEN}Starting services...${NC}"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${CYAN}[BACKEND]${NC} Starting OpenCode backend..."
cd opencode-backend/packages/console/app
bun dev > /dev/null 2>&1 &
BACKEND_PID=$!
cd ../../..

# Wait a moment for backend to initialize
sleep 2

# Start frontend
echo -e "${MAGENTA}[FRONTEND]${NC} Starting Mercury Coder..."
cd mercury-coder
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Services started successfully!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo -e "${CYAN}Backend PID: ${BACKEND_PID}${NC}"
echo -e "${MAGENTA}Frontend PID: ${FRONTEND_PID}${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all background processes
wait