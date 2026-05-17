#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "\n${CYAN}=== $1 ===${NC}\n"; }

detect_system() {
    if [ -d "$PREFIX" ] && [ -f "$PREFIX/bin/bash" ]; then
        echo "termux"
        return
    fi
    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        echo "docker"
        return
    fi
    if command -v apt-get &> /dev/null; then echo "debian"; return; fi
    if command -v yum &> /dev/null; then echo "redhat"; return; fi
    if command -v dnf &> /dev/null; then echo "redhat"; return; fi
    if command -v pacman &> /dev/null; then echo "arch"; return; fi
    if command -v apk &> /dev/null; then echo "alpine"; return; fi
    if command -v brew &> /dev/null; then echo "macos"; return; fi
    echo "unknown"
}

detect_china() {
    if command -v curl &> /dev/null; then
        COUNTRY=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "unknown")
        [ "$COUNTRY" = "CN" ] && echo "china" || echo "global"
    else
        echo "global"
    fi
}

setup_mirrors() {
    REGION=$(detect_china)
    if [ "$REGION" = "china" ]; then
        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120

[install]
trusted-host = mirrors.aliyun.com
EOF
        npm config set registry https://registry.npmmirror.com 2>/dev/null || true
        # GitHub mirror for China
        git config --global url."https://ghproxy.com/https://github.com/".insteadOf "https://github.com/" 2>/dev/null || true
    else
        # Reset git mirror if outside China
        git config --global --unset-all url."https://ghproxy.com/https://github.com/".insteadOf 2>/dev/null || true
    fi
}

create_directories() {
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups}
}

check_env() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null) || \
                     SECRET_KEY=$(openssl rand -hex 32 2>/dev/null) || \
                     SECRET_KEY="dev-secret-key-$(date +%s)"
        cat > "$SCRIPT_DIR/.env" << EOF
SECRET_KEY=$SECRET_KEY
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=./data
BOOKS_DIR=./data/books
INDEX_DIR=./data/index
STATIC_DIR=./data/static
LOGS_DIR=./data/logs
CACHE_DIR=./data/cache
EOF
        print_success ".env created"
    fi
}

ensure_rust_termux() {
    if command -v rustc &> /dev/null; then
        print_success "Rust: $(rustc --version)"
        return 0
    fi

    print_info "Installing Rust (needed for pydantic-core)..."
    pkg install -y rust cmake

    if command -v rustc &> /dev/null; then
        print_success "Rust: $(rustc --version)"
    else
        print_error "Rust install failed"
        return 1
    fi
}

pip_install_one() {
    local pkg="$1"
    local desc="$2"
    print_info "[$desc] $pkg ..."
    if pip install "$pkg" 2>&1; then
        print_success "$pkg installed"
    else
        print_warning "$pkg failed (non-critical, continuing)"
    fi
}

install_termux_deps() {
    print_header "Termux Setup"

    print_info "Updating packages..."
    pkg update -y 2>/dev/null || true

    print_info "Installing base tools + Rust..."
    pkg install -y python python-pip nodejs-lts npm git curl wget rust cmake 2>/dev/null || true

    ensure_rust_termux

    setup_mirrors
    create_directories
    check_env

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "Creating venv..."
        python -m venv venv
    fi

    source venv/bin/activate

    print_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel

    print_header "Install Python Packages"
    print_info "Installing packages one by one (with progress)..."

    pip_install_one "fastapi==0.110.0" "1/18"
    pip_install_one "uvicorn[standard]==0.27.1" "2/18"
    pip_install_one "sqlalchemy==2.0.27" "3/18"
    pip_install_one "aiosqlite==0.19.0" "4/18"
    pip_install_one "redis==5.0.1" "5/18"

    echo ""
    print_warning "========================================="
    print_warning "  Next: pydantic (compiles from source)"
    print_warning "  This takes 10-30 min on ARM Android"
    print_warning "  Please wait, do NOT cancel!"
    print_warning "========================================="
    echo ""
    pip_install_one "pydantic==2.6.1" "6/18"

    pip_install_one "pydantic-settings==2.1.0" "7/18"
    pip_install_one "python-multipart==0.0.9" "8/18"
    pip_install_one "beautifulsoup4==4.12.3" "9/18"
    pip_install_one "tenacity==8.2.3" "10/18"
    pip_install_one "rich==13.7.0" "11/18"
    pip_install_one "python-jose[cryptography]==3.3.0" "12/18"
    pip_install_one "pycryptodome==3.20.0" "13/18"
    pip_install_one "passlib==1.7.4" "14/18"
    pip_install_one "bcrypt==4.1.2" "15/18"
    pip_install_one "aiohttp==3.9.3" "16/18"
    pip_install_one "httpx==0.27.0" "17/18"
    pip_install_one "aiofiles==23.2.1" "18/18"

    deactivate
    cd "$SCRIPT_DIR"

    print_success "All dependencies installed!"
}

install_docker_deps() {
    print_header "Docker Setup"
    if ! command -v docker &> /dev/null; then
        print_error "Docker not installed"
        exit 1
    fi
    setup_mirrors
    create_directories
    check_env
    print_info "Building and starting..."
    docker-compose up -d
    print_success "Services started"
    print_info "App: http://localhost"
    print_info "API docs: http://localhost:8000/docs"
}

install_native_deps() {
    print_header "Native Setup"
    SYSTEM=$(detect_system)
    setup_mirrors
    create_directories
    check_env

    case "$SYSTEM" in
        debian)
            sudo apt-get update -qq 2>/dev/null || true
            sudo apt-get install -y python3 python3-venv python3-pip nodejs npm redis-server curl git 2>/dev/null || true
            ;;
        redhat)
            sudo yum install -y python3 python3-pip nodejs npm redis curl git 2>/dev/null || true
            ;;
        arch)
            sudo pacman -Sy --noconfirm python python-pip nodejs npm redis curl git 2>/dev/null || true
            ;;
        alpine)
            apk add --no-cache python3 py3-pip nodejs npm redis curl git 2>/dev/null || true
            ;;
        macos)
            command -v brew &> /dev/null && brew install python node redis 2>/dev/null || true
            ;;
    esac

    cd "$BACKEND_DIR"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    cd "$SCRIPT_DIR"

    print_success "Dependencies installed"
}

start_termux_services() {
    print_header "Start Services (Termux)"

    # Keep Android awake so network doesn't drop
    if command -v termux-wake-lock &> /dev/null; then
        termux-wake-lock 2>/dev/null || true
        print_info "Wake lock acquired (prevents sleep)"
    fi

    if ! pgrep -x redis-server > /dev/null 2>&1; then
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes --port 6379 --maxmemory 64mb --maxmemory-policy allkeys-lru 2>/dev/null || true
        fi
    fi

    cd "$BACKEND_DIR"
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    source venv/bin/activate

    export DATABASE_URL="sqlite+aiosqlite:///data/novel.db"
    export REDIS_URL="redis://localhost:6379"
    export PYTHONDONTWRITEBYTECODE=1

    # Termux needs explicit host binding for external access
    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers > ../data/logs/backend.log 2>&1 &
    echo $! > uvicorn.pid

    deactivate
    cd "$SCRIPT_DIR"

    print_info "Waiting for backend..."
    for i in $(seq 1 30); do
        curl -s http://localhost:8000/api/health > /dev/null 2>&1 && break
        sleep 1
    done

    print_success "Services started"
    print_info "App (frontend + API): http://localhost:8000"
    print_info "API docs: http://localhost:8000/docs"
    
    # Get all possible access addresses
    IP_ADDR=$(ifconfig wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' || echo "")
    if [ -n "$IP_ADDR" ]; then
        print_info "LAN access: http://$IP_ADDR:8000"
    fi
    
    # Auto-open browser on Android if possible
    if command -v termux-open-url &> /dev/null; then
        print_info "Opening browser..."
        termux-open-url "http://localhost:8000" 2>/dev/null || true
    fi
    
    print_warning "If browser cannot connect, run: ./start.sh tunnel"
}

start_native_services() {
    print_header "Start Services"

    if ! pgrep -x redis-server > /dev/null 2>&1; then
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes --port 6379 --maxmemory 64mb --maxmemory-policy allkeys-lru 2>/dev/null || true
        fi
    fi

    cd "$BACKEND_DIR"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate

    export DATABASE_URL="sqlite+aiosqlite:///data/novel.db"
    export REDIS_URL="redis://localhost:6379"
    export PYTHONDONTWRITEBYTECODE=1

    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../data/logs/backend.log 2>&1 &
    echo $! > uvicorn.pid

    deactivate
    cd "$SCRIPT_DIR"

    print_info "Waiting for backend..."
    for i in $(seq 1 30); do
        curl -s http://localhost:8000/api/health > /dev/null 2>&1 && break
        sleep 1
    done

    print_success "Services started"
    print_info "App: http://localhost:8000"
    print_info "API docs: http://localhost:8000/docs"
}

stop_services() {
    print_header "Stop Services"

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid"
    fi
    pkill -f "uvicorn" 2>/dev/null || true
    docker-compose down 2>/dev/null || true
    if command -v redis-cli &> /dev/null; then
        redis-cli shutdown 2>/dev/null || true
    fi

    # Release wake lock on Termux
    if command -v termux-wake-unlock &> /dev/null; then
        termux-wake-unlock 2>/dev/null || true
        print_info "Wake lock released"
    fi

    # Stop any active tunnel
    stop_tunnel 2>/dev/null || true

    print_success "All services stopped"
}

diagnose_network() {
    print_header "Network Diagnosis"
    
    print_info "Checking if backend is running..."
    if pgrep -f "uvicorn" > /dev/null; then
        print_success "Backend process found"
    else
        print_error "Backend not running!"
        return 1
    fi
    
    print_info "Checking localhost:8000..."
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "localhost:8000 is responding"
    else
        print_error "localhost:8000 not responding"
    fi
    
    print_info "Checking network interfaces..."
    IP_ADDR=$(ifconfig wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}' || echo "")
    if [ -n "$IP_ADDR" ]; then
        print_info "WiFi IP: $IP_ADDR"
        print_info "Testing $IP_ADDR:8000..."
        if curl -s --connect-timeout 3 http://$IP_ADDR:8000/api/health > /dev/null 2>&1; then
            print_success "$IP_ADDR:8000 is accessible"
        else
            print_error "$IP_ADDR:8000 not accessible (firewall?)"
        fi
    else
        print_warning "No WiFi IP found"
    fi
    
    print_info "Checking listening ports..."
    netstat -tlnp 2>/dev/null | grep 8000 || ss -tlnp 2>/dev/null | grep 8000 || print_warning "Cannot check ports"
    
    print_info "Checking Termux network properties..."
    if [ -n "$TERMUX_VERSION" ]; then
        print_info "TERMUX_VERSION: $TERMUX_VERSION"
    fi
    if [ -f /proc/net/netstat ]; then
        print_success "Network stack accessible"
    fi
}

start_tunnel() {
    print_header "Start Public Tunnel"
    
    if ! pgrep -f "uvicorn" > /dev/null; then
        print_error "Backend not running! Start services first: ./start.sh start"
        return 1
    fi
    
    # Try cloudflared first (most reliable)
    if command -v cloudflared &> /dev/null; then
        print_info "Starting Cloudflare tunnel..."
        cloudflared tunnel --url http://localhost:8000 2>&1 | tee /tmp/tunnel.log &
        TUNNEL_PID=$!
        echo $TUNNEL_PID > /tmp/tunnel.pid
        sleep 5
        URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/tunnel.log | head -1)
        if [ -n "$URL" ]; then
            print_success "Public URL: $URL"
            if command -v termux-open-url &> /dev/null; then
                termux-open-url "$URL" 2>/dev/null || true
            fi
            return 0
        fi
    fi
    
    # Try localtunnel via npx
    if command -v npx &> /dev/null; then
        print_info "Starting localtunnel..."
        npx -y localtunnel --port 8000 2>&1 | tee /tmp/tunnel.log &
        TUNNEL_PID=$!
        echo $TUNNEL_PID > /tmp/tunnel.pid
        sleep 5
        URL=$(grep -o 'https://[a-z0-9-]*\.loca\.lt' /tmp/tunnel.log | head -1)
        if [ -n "$URL" ]; then
            print_success "Public URL: $URL"
            if command -v termux-open-url &> /dev/null; then
                termux-open-url "$URL" 2>/dev/null || true
            fi
            return 0
        fi
    fi
    
    # Try serveo.net SSH tunnel
    if command -v ssh &> /dev/null; then
        print_info "Starting SSH tunnel (serveo.net)..."
        print_warning "Press Enter when you see the URL..."
        ssh -o StrictHostKeyChecking=no -R 80:localhost:8000 serveo.net 2>&1 | tee /tmp/tunnel.log &
        TUNNEL_PID=$!
        echo $TUNNEL_PID > /tmp/tunnel.pid
        sleep 8
        URL=$(grep -o 'https://[a-z0-9-]*\.serveo\.net' /tmp/tunnel.log | head -1)
        if [ -n "$URL" ]; then
            print_success "Public URL: $URL"
            return 0
        fi
    fi
    
    print_error "No tunnel method available"
    print_info "Install one of: cloudflared, nodejs (for npx), or ensure ssh works"
    return 1
}

stop_tunnel() {
    if [ -f /tmp/tunnel.pid ]; then
        kill $(cat /tmp/tunnel.pid) 2>/dev/null || true
        rm -f /tmp/tunnel.pid
        print_success "Tunnel stopped"
    else
        print_warning "No tunnel running"
    fi
}

show_status() {
    print_header "Service Status"
    SYSTEM=$(detect_system)
    echo "System: $SYSTEM"

    pgrep -f "uvicorn" > /dev/null && print_success "App: running on :8000" || print_error "App: stopped"
    echo ""
    curl -s http://localhost:8000/api/health > /dev/null 2>&1 && print_success "API: responding" || print_error "API: not responding"
}

git_pull_with_retry() {
    local max_retries=3
    local timeout=30
    local attempt=1

    while [ $attempt -le $max_retries ]; do
        print_info "Pull attempt $attempt/$max_retries (timeout: ${timeout}s)..."
        if timeout $timeout git pull origin main 2>&1; then
            return 0
        fi
        attempt=$((attempt + 1))
        if [ $attempt -le $max_retries ]; then
            print_warning "Attempt failed, retrying in 3s..."
            sleep 3
        fi
    done
    return 1
}

update_repo() {
    print_header "Update Repository"

    cd "$SCRIPT_DIR"

    if [ ! -d ".git" ]; then
        print_error "Not a git repository"
        return 1
    fi

    # Set git timeout globally
    git config --global http.lowSpeedLimit 1000 2>/dev/null || true
    git config --global http.lowSpeedTime 10 2>/dev/null || true

    # Detect region and setup mirror before pull
    setup_mirrors

    print_info "Fetching updates..."
    if git_pull_with_retry; then
        print_success "Repository updated"
        return 0
    fi

    print_warning "Direct pull failed, trying GitHub mirror..."
    git config --global url."https://ghproxy.com/https://github.com/".insteadOf "https://github.com/" 2>/dev/null || true
    if git_pull_with_retry; then
        print_success "Repository updated via mirror"
        return 0
    fi

    print_warning "Mirror also failed, trying fetch + reset..."
    if timeout 30 git fetch origin main 2>&1; then
        git reset --hard origin/main 2>&1
        print_success "Repository updated via fetch+reset"
        return 0
    fi

    print_error "All methods failed. Try manually:"
    print_info "  git config --global url.\"https://ghproxy.com/https://github.com/\".insteadOf \"https://github.com/\""
    print_info "  git pull origin main"
    print_info "  or: git fetch origin && git reset --hard origin/main"
    return 1
}

show_help() {
    cat << EOF
Novel Reader Launcher

Usage: ./start.sh [command]

Commands:
  install     Detect system and install dependencies
  start       Start all services
  stop        Stop all services
  status      Show service status
  diagnose    Network diagnosis (Termux)
  tunnel      Create public URL for external access
  tunnel-stop Stop public tunnel
  update      Update code from GitHub (auto mirror for China)

Supported systems:
  - Termux (Android)
  - Docker
  - Linux (Debian/RHEL/Arch/Alpine)
  - macOS

Examples:
  ./start.sh install
  ./start.sh start
  ./start.sh status
  ./start.sh diagnose
  ./start.sh tunnel
  ./start.sh update
EOF
}

main() {
    SYSTEM=$(detect_system)
    print_info "Detected system: $SYSTEM"

    case "${1:-}" in
        install)
            case "$SYSTEM" in
                termux) install_termux_deps ;;
                docker) install_docker_deps ;;
                *) install_native_deps ;;
            esac
            ;;
        start)
            case "$SYSTEM" in
                termux) start_termux_services ;;
                docker)
                    docker-compose up -d
                    print_success "Docker services started"
                    ;;
                *) start_native_services ;;
            esac
            ;;
        stop)
            stop_services
            ;;
        status)
            show_status
            ;;
        diagnose)
            diagnose_network
            ;;
        tunnel)
            start_tunnel
            ;;
        tunnel-stop)
            stop_tunnel
            ;;
        update)
            update_repo
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
