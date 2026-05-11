#!/bin/bash
# Novel Reader - Termux (Android) Deployment Script
# Optimized for Termux environment, no root required

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_INSTALL=false
USE_REDIS=false

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -s, --skip      Skip dependency installation"
    echo "  -r, --redis     Install and start Redis"
    echo "  -h, --help      Show this help"
    echo ""
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--skip)
            SKIP_INSTALL=true
            shift
            ;;
        -r|--redis)
            USE_REDIS=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo -e "${MAGENTA}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║      Novel Reader - Termux/Android Deployment Script v1.0  ║
║  Optimized for Termux, no root required                   ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

log_step() {
    echo -e "\n${CYAN}=== $1 ===${NC}"
}

log_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

log_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

is_termux() {
    [ -d "$PREFIX" ] && [ -f "$PREFIX/bin/pkg" ]
}

check_termux() {
    if ! is_termux; then
        log_error "This script is designed for Termux"
        exit 1
    fi
}

install_termux_deps() {
    log_step "Updating Termux repositories"
    pkg update -y
    pkg upgrade -y

    log_step "Installing base tools"
    pkg install -y \
        python \
        python-pip \
        python-venv \
        git \
        curl \
        termux-exec \
        openssh \
        openssl \
        file \
        coreutils \
        findutils \
        diffutils \
        grep \
        sed \
        util-linux \
        libcrypt \
        libffi \
        libxml2 \
        libxslt \
        zlib

    log_step "Installing build tools"
    pkg install -y \
        clang \
        make \
        cmake \
        setuptools \
        libc++

    log_step "Installing Python dependencies"
    pip install --upgrade pip wheel setuptools

    log_step "Installing cryptography pre-built version"
    pip install --only-binary=cryptography cryptography -q || pip install cryptography -q

    log_step "Installing project dependencies"
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements.txt"
    elif [ -f "$PROJECT_ROOT/backend/requirements-crossplatform.txt" ]; then
        pip install -r "$PROJECT_ROOT/backend/requirements-crossplatform.txt"
    elif [ -f "$PROJECT_ROOT/backend/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    fi

    log_success "Dependencies installed"
}

init_data_dirs() {
    log_step "Initializing data directories"
    mkdir -p "$PROJECT_ROOT/data"/{books,index,static,logs,cache}
    log_success "Data directories initialized"
}

setup_env_file() {
    log_step "Configuring environment variables"
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        else
            cat > "$PROJECT_ROOT/.env" << 'ENVEOF'
SECRET_KEY=change-me-in-production-termux
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
ENVEOF
        fi
        log_success ".env file created"
    else
        log_warning ".env file exists"
    fi
}

install_redis_termux() {
    if [ "$USE_REDIS" = true ]; then
        log_step "Installing Redis"
        pkg install -y redis

        if ! pgrep -x redis-server > /dev/null; then
            log_step "Starting Redis service"
            redis-server --daemonize yes --port 6379 --maxmemory 32mb --maxmemory-policy allkeys-lru
            log_success "Redis service started"
        else
            log_warning "Redis service already running"
        fi
    fi
}

create_start_script() {
    log_step "Creating convenience start script"
    cat > "$PROJECT_ROOT/start-termux.sh" << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
export PYTHONPATH="$PWD/backend:$PWD"
export DATA_DIR="$PWD/data"
export LOG_LEVEL=INFO
export TERMUX=1
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
SCRIPT
    chmod +x "$PROJECT_ROOT/start-termux.sh"
    log_success "Start script created: ./start-termux.sh"
}

start_backend() {
    log_step "Starting backend service"

    export PYTHONPATH="$PROJECT_ROOT/backend:$PROJECT_ROOT"
    export DATA_DIR="$PROJECT_ROOT/data"
    export BOOKS_DIR="$PROJECT_ROOT/data/books"
    export LOG_LEVEL="INFO"
    export TERMUX=1

    cd "$PROJECT_ROOT/backend"

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}     Novel Reader Backend Starting...${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "Access URLs:"
    echo -e "  ${CYAN}Backend: http://localhost:8000${NC}"
    echo -e "  ${CYAN}API Docs: http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""

    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

main() {
    check_termux

    if [ "$SKIP_INSTALL" = false ]; then
        install_termux_deps
    fi

    init_data_dirs
    setup_env_file
    create_start_script
    install_redis_termux

    log_success "Environment setup complete!"

    echo ""
    echo -e "${CYAN}Quick start commands:${NC}"
    echo -e "  cd $PROJECT_ROOT"
    echo -e "  ./start-termux.sh"
    echo ""

    read -p "Start service now? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        start_backend
    fi
}

main
