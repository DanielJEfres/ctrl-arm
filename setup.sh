#!/bin/bash

# Ctrl-Arm Frontend Setup Script
# Sets up the Electron frontend application

set -e

echo "🚀 Setting up Ctrl-Arm Frontend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Node.js is installed
check_node() {
    print_status "Checking Node.js installation..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION found"
    else
        print_error "Node.js is required but not installed. Please install Node.js 18+ and try again."
        exit 1
    fi
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    cd frontend
    
    # Install npm dependencies
    print_status "Installing npm dependencies..."
    npm install
    
    print_success "Frontend setup complete"
    cd ..
}

# Main setup process
main() {
    echo "=========================================="
    echo "    Ctrl-Arm Frontend Setup"
    echo "=========================================="
    echo ""
    
    check_node
    echo ""
    
    setup_frontend
    echo ""
    
    print_success "🎉 Setup complete!"
    echo ""
    echo "To start the application, run:"
    echo "  cd frontend && npm run dev"
    echo ""
    echo "The Electron app will appear as a semi-transparent overlay window."
    echo "It will use filler data for now (no backend connection)."
}

# Run main function
main "$@"
