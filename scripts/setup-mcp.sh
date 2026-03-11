#!/bin/bash
# kubectl-ai MCP Server Setup Script
# This script configures kubectl-ai as an MCP server for Cursor IDE

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         kubectl-ai MCP Server Setup                        ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Project directory: ${PROJECT_DIR}${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.10+${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found: $(python3 --version)${NC}"

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed. Please install kubectl${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl found: $(kubectl version --client --short 2>/dev/null || kubectl version --client | head -1)${NC}"

# Check kubeconfig
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"
if [ ! -f "$KUBECONFIG_PATH" ]; then
    echo -e "${RED}❌ Kubeconfig not found at: $KUBECONFIG_PATH${NC}"
    echo -e "${YELLOW}   Set KUBECONFIG environment variable or create ~/.kube/config${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Kubeconfig found: $KUBECONFIG_PATH${NC}"

# Create virtual environment if it doesn't exist
echo -e "\n${YELLOW}Setting up virtual environment...${NC}"
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
fi
echo -e "${GREEN}✓ Virtual environment ready${NC}"

# Activate and install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
source "$PROJECT_DIR/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_DIR/requirements.txt"
pip install --quiet mcp
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Get the Python path
PYTHON_PATH="$PROJECT_DIR/venv/bin/python3"

# Create MCP configuration
echo -e "\n${YELLOW}Configuring MCP server...${NC}"

MCP_CONFIG_DIR="$HOME/.cursor"
MCP_CONFIG_FILE="$MCP_CONFIG_DIR/mcp.json"

# Create directory if it doesn't exist
mkdir -p "$MCP_CONFIG_DIR"

# Check if mcp.json exists
if [ -f "$MCP_CONFIG_FILE" ]; then
    echo -e "${YELLOW}Existing mcp.json found. Backing up to mcp.json.backup${NC}"
    cp "$MCP_CONFIG_FILE" "$MCP_CONFIG_FILE.backup"
    
    # Check if kubectl-ai is already configured
    if grep -q "kubectl-ai" "$MCP_CONFIG_FILE"; then
        echo -e "${YELLOW}kubectl-ai already exists in mcp.json. Updating...${NC}"
        # Use Python to update the JSON
        python3 << EOF
import json

with open("$MCP_CONFIG_FILE", "r") as f:
    config = json.load(f)

config["mcpServers"]["kubectl-ai"] = {
    "command": "$PYTHON_PATH",
    "args": ["$PROJECT_DIR/src/mcp_server.py"],
    "env": {
        "KUBECONFIG": "$KUBECONFIG_PATH",
        "PYTHONPATH": "$PROJECT_DIR"
    }
}

with open("$MCP_CONFIG_FILE", "w") as f:
    json.dump(config, f, indent=2)
EOF
    else
        # Add kubectl-ai to existing config
        python3 << EOF
import json

with open("$MCP_CONFIG_FILE", "r") as f:
    config = json.load(f)

if "mcpServers" not in config:
    config["mcpServers"] = {}

config["mcpServers"]["kubectl-ai"] = {
    "command": "$PYTHON_PATH",
    "args": ["$PROJECT_DIR/src/mcp_server.py"],
    "env": {
        "KUBECONFIG": "$KUBECONFIG_PATH",
        "PYTHONPATH": "$PROJECT_DIR"
    }
}

with open("$MCP_CONFIG_FILE", "w") as f:
    json.dump(config, f, indent=2)
EOF
    fi
else
    # Create new mcp.json
    cat > "$MCP_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "kubectl-ai": {
      "command": "$PYTHON_PATH",
      "args": ["$PROJECT_DIR/src/mcp_server.py"],
      "env": {
        "KUBECONFIG": "$KUBECONFIG_PATH",
        "PYTHONPATH": "$PROJECT_DIR"
      }
    }
  }
}
EOF
fi

echo -e "${GREEN}✓ MCP configuration created at: $MCP_CONFIG_FILE${NC}"

# Test the MCP server
echo -e "\n${YELLOW}Testing MCP server...${NC}"
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR" "$PYTHON_PATH" -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from src.mcp_server import server, list_tools
import asyncio

tools = asyncio.run(list_tools())
print(f'✓ MCP server loaded successfully with {len(tools)} tools')
" 2>/dev/null || {
    echo -e "${RED}❌ MCP server test failed${NC}"
    exit 1
}

echo -e "${GREEN}✓ MCP server test passed${NC}"

# Print success message
echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         Setup Complete! 🎉                                  ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. ${BLUE}Restart Cursor IDE${NC} (Cmd+Q, then reopen)"
echo -e "  2. Open a new chat in Cursor"
echo -e "  3. Ask Claude: ${BLUE}\"Show me all pods in my cluster\"${NC}"
echo ""
echo -e "${YELLOW}Available commands:${NC}"
echo -e "  • kubectl_get - List resources"
echo -e "  • kubectl_describe - Get details"
echo -e "  • kubectl_logs - View logs"
echo -e "  • cluster_health - Health check"
echo -e "  • security_audit - Security scan"
echo ""
echo -e "${YELLOW}To use the CLI version instead:${NC}"
echo -e "  cd $PROJECT_DIR"
echo -e "  source venv/bin/activate"
echo -e "  python -m src.main chat"
echo ""
