#!/bin/bash

MIRROR_CACHE_DIR=""
MIRROR_CACHE_FILE=""
CACHE_TTL=86400

PIP_MIRRORS=(
    "https://pypi.org/simple"
    "https://mirrors.aliyun.com/pypi/simple"
    "https://pypi.tuna.tsinghua.edu.cn/simple"
    "https://mirrors.cloud.tencent.com/pypi/simple"
    "https://repo.huaweicloud.com/repository/pypi/simple"
    "https://mirror.nju.edu.cn/pypi/web/simple"
    "https://mirror.hit.edu.cn/pypi/web/simple"
    "https://mirrors.ustc.edu.cn/pypi/web/simple"
    "https://mirror.sjtu.edu.cn/pypi/web/simple"
    "https://mirrors.hit.edu.cn/pypi/web/simple"
)

NPM_MIRRORS=(
    "https://registry.npmjs.org"
    "https://registry.npmmirror.com"
    "https://mirrors.huaweicloud.com/repository/npm/"
    "https://mirrors.tencent.com/npm/"
    "https://registry.npm.taobao.org"
    "https://skimdb.npmjs.com/registry"
    "https://registry.npmjs.org.au"
    "https://registry.npmjs.eu"
    "https://npm.iran.liara.run"
    "https://registry.npmjs.cf"
)

TERMUX_MIRRORS=(
    "https://packages.termux.dev/apt/termux-main"
    "https://mirrors.tuna.tsinghua.edu.cn/termux/apt/termux-main"
    "https://mirrors.aliyun.com/termux/termux-main"
    "https://mirrors.hit.edu.cn/termux/termux-main"
    "https://mirrors.ustc.edu.cn/termux/termux-main"
    "https://mirrors.nju.edu.cn/termux/termux-main"
    "https://mirror.nju.edu.cn/termux/termux-main"
    "https://mirrors.bfsu.edu.cn/termux/termux-main"
    "https://mirrors.sjtug.sjtu.edu.cn/termux/termux-main"
    "https://mirrors.hit.edu.cn/termux/termux-main"
)

DOCKER_MIRRORS=(
    "https://registry-1.docker.io"
    "https://docker.m.daocloud.io"
    "https://dockerhub.azk8s.cn"
    "https://hub-mirror.c.163.com"
    "https://mirror.baidubce.com"
    "https://docker.mirrors.ustc.edu.cn"
    "https://reg-mirror.qiniu.com"
    "https://dockerproxy.com"
    "https://docker.nju.edu.cn"
    "https://docker.mirrors.sjtug.sjtu.edu.cn"
)

mirror_print_info() { echo -e "\033[0;34m[MIRROR]\033[0m $1"; }
mirror_print_ok() { echo -e "\033[0;32m[MIRROR]\033[0m $1"; }
mirror_print_warn() { echo -e "\033[1;33m[MIRROR]\033[0m $1"; }

init_mirror_cache() {
    MIRROR_CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/novel-reader"
    MIRROR_CACHE_FILE="$MIRROR_CACHE_DIR/mirror_cache"
    mkdir -p "$MIRROR_CACHE_DIR"
}

is_cache_valid() {
    local key="$1"
    if [ ! -f "$MIRROR_CACHE_FILE" ]; then
        return 1
    fi
    local cached_line cached_time current_time
    current_time=$(date +%s)
    cached_line=$(grep "^$key|" "$MIRROR_CACHE_FILE" 2>/dev/null | head -1)
    if [ -z "$cached_line" ]; then
        return 1
    fi
    cached_time=$(echo "$cached_line" | cut -d'|' -f2 | cut -d'=' -f2)
    local age=$((current_time - cached_time))
    if [ "$age" -lt "$CACHE_TTL" ]; then
        return 0
    fi
    return 1
}

get_cached_mirror() {
    local key="$1"
    local cached_line
    cached_line=$(grep "^$key|" "$MIRROR_CACHE_FILE" 2>/dev/null | head -1)
    if [ -n "$cached_line" ]; then
        echo "$cached_line" | cut -d'|' -f3 | cut -d'=' -f2-
    fi
}

save_mirror_cache() {
    local key="$1"
    local value="$2"
    local current_time
    current_time=$(date +%s)
    if [ -f "$MIRROR_CACHE_FILE" ]; then
        sed -i "/^$key|/d" "$MIRROR_CACHE_FILE" 2>/dev/null || true
    fi
    echo "$key|time=$current_time|url=$value" >> "$MIRROR_CACHE_FILE"
}

test_single_url() {
    local url="$1"
    local timeout=5
    local start_time end_time elapsed

    if command -v curl &> /dev/null; then
        start_time=$(date +%s%N 2>/dev/null || date +%s)
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$timeout" --max-time "$timeout" -L "$url" 2>/dev/null)
        end_time=$(date +%s%N 2>/dev/null || date +%s)

        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ] 2>/dev/null; then
            if echo "$start_time" | grep -q "N$"; then
                elapsed=$(( (end_time - start_time) / 1000000 ))
            else
                elapsed=$(( end_time - start_time ))
                elapsed=$(( elapsed * 1000 ))
            fi
            echo "$elapsed"
            return 0
        fi
    elif command -v wget &> /dev/null; then
        start_time=$(date +%s%N 2>/dev/null || date +%s)
        wget -q --timeout="$timeout" -O /dev/null "$url" 2>/dev/null
        if [ $? -eq 0 ]; then
            end_time=$(date +%s%N 2>/dev/null || date +%s)
            if echo "$start_time" | grep -q "N$"; then
                elapsed=$(( (end_time - start_time) / 1000000 ))
            else
                elapsed=$(( end_time - start_time ))
                elapsed=$(( elapsed * 1000 ))
            fi
            echo "$elapsed"
            return 0
        fi
    fi

    echo "999999"
    return 1
}

select_best_mirror() {
    local mirror_type="$1"
    shift
    local mirrors=("$@")
    local best_url=""
    best_url=""
    local best_time=999999
    local results=()

    mirror_print_info "测试 ${#mirrors[@]} 个 ${mirror_type} 镜像源..."

    local tmp_dir
    tmp_dir=$(mktemp -d)
    local idx=0

    for url in "${mirrors[@]}"; do
        (
            local elapsed
            elapsed=$(test_single_url "$url")
            echo "${elapsed}|${url}" > "$tmp_dir/result_${idx}"
        ) &
        idx=$((idx + 1))
    done

    wait

    for i in $(seq 0 $((idx - 1))); do
        if [ -f "$tmp_dir/result_${i}" ]; then
            local result
            result=$(cat "$tmp_dir/result_${i}")
            results+=("$result")
            local r_time
            r_time=$(echo "$result" | cut -d'|' -f1)
            local r_url
            r_url=$(echo "$result" | cut -d'|' -f2-)
            if [ "$r_time" -lt "$best_time" ] 2>/dev/null; then
                best_time=$r_time
                best_url=$r_url
            fi
        fi
    done

    rm -rf "$tmp_dir"

    if [ -z "$best_url" ] || [ "$best_time" -ge 999999 ]; then
        mirror_print_warn "所有镜像源均不可达，使用默认源"
        echo "${mirrors[0]}"
        return 1
    fi

    local best_time_display
    if [ "$best_time" -gt 1000 ]; then
        best_time_display="$((best_time / 1000))s"
    else
        best_time_display="${best_time}ms"
    fi
    mirror_print_ok "最快 ${mirror_type} 镜像: $best_url (${best_time_display})"

    save_mirror_cache "$mirror_type" "$best_url"

    echo "$best_url"
    return 0
}

select_pip_mirror() {
    init_mirror_cache
    if is_cache_valid "pip"; then
        local cached
        cached=$(get_cached_mirror "pip")
        if [ -n "$cached" ]; then
            mirror_print_ok "使用缓存的 pip 镜像: $cached"
            echo "$cached"
            return 0
        fi
    fi
    select_best_mirror "pip" "${PIP_MIRRORS[@]}"
}

select_npm_mirror() {
    init_mirror_cache
    if is_cache_valid "npm"; then
        local cached
        cached=$(get_cached_mirror "npm")
        if [ -n "$cached" ]; then
            mirror_print_ok "使用缓存的 npm 镜像: $cached"
            echo "$cached"
            return 0
        fi
    fi
    select_best_mirror "npm" "${NPM_MIRRORS[@]}"
}

select_termux_mirror() {
    init_mirror_cache
    if is_cache_valid "termux"; then
        local cached
        cached=$(get_cached_mirror "termux")
        if [ -n "$cached" ]; then
            mirror_print_ok "使用缓存的 Termux 镜像: $cached"
            echo "$cached"
            return 0
        fi
    fi
    select_best_mirror "termux" "${TERMUX_MIRRORS[@]}"
}

select_docker_mirror() {
    init_mirror_cache
    if is_cache_valid "docker"; then
        local cached
        cached=$(get_cached_mirror "docker")
        if [ -n "$cached" ]; then
            mirror_print_ok "使用缓存的 Docker 镜像: $cached"
            echo "$cached"
            return 0
        fi
    fi
    select_best_mirror "docker" "${DOCKER_MIRRORS[@]}"
}

configure_pip_mirror() {
    local mirror_url
    mirror_url=$(select_pip_mirror)

    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << EOF
[global]
index-url = $mirror_url
trusted-host = $(echo "$mirror_url" | sed 's|https://||' | cut -d'/' -f1)
timeout = 120
retries = 5
EOF
    mirror_print_ok "pip 已配置镜像: $mirror_url"
}

configure_npm_mirror() {
    local mirror_url
    mirror_url=$(select_npm_mirror)

    npm config set registry "$mirror_url" 2>/dev/null || true
    mirror_print_ok "npm 已配置镜像: $mirror_url"
}

configure_termux_mirror() {
    local mirror_url
    mirror_url=$(select_termux_mirror)

    local termux_dir="$PREFIX/etc/apt"
    if [ -d "$termux_dir" ]; then
        cat > "$termux_dir/sources.list" << EOF
deb $mirror_url stable main
EOF
        mirror_print_ok "Termux pkg 已配置镜像: $mirror_url"
        pkg update -y 2>/dev/null || true
    fi
}

configure_docker_mirror() {
    local mirror_url
    mirror_url=$(select_docker_mirror)

    local docker_config_dir="/etc/docker"
    local docker_config="$docker_config_dir/daemon.json"

    if [ -f "$docker_config" ]; then
        if grep -q "registry-mirrors" "$docker_config"; then
            mirror_print_info "Docker 镜像已配置，跳过"
            return 0
        fi
    fi

    mirror_print_info "Docker 镜像加速配置 (需要 sudo):"
    mirror_print_info "  $mirror_url"
    mirror_print_info "手动配置: 编辑 /etc/docker/daemon.json 添加:"
    cat << JSONEOF
{
  "registry-mirrors": ["$mirror_url"]
}
JSONEOF
}

configure_all_mirrors() {
    local sys_type="${1:-linux}"

    mirror_print_info "========== 镜像源自动选择 =========="

    if command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
        configure_pip_mirror
    fi

    if command -v npm &> /dev/null; then
        configure_npm_mirror
    fi

    if [ "$sys_type" = "termux" ]; then
        configure_termux_mirror
    fi

    if [ "$sys_type" != "termux" ] && command -v docker &> /dev/null; then
        configure_docker_mirror
    fi

    mirror_print_info "========== 镜像源配置完成 =========="
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-all}" in
        pip)    select_pip_mirror ;;
        npm)    select_npm_mirror ;;
        termux) select_termux_mirror ;;
        docker) select_docker_mirror ;;
        configure)
            shift
            configure_all_mirrors "${1:-linux}"
            ;;
        all)
            configure_all_mirrors "$(uname -s | tr '[:upper:]' '[:lower:]')"
            ;;
        *)
            echo "用法: $0 {pip|npm|termux|docker|configure|all}"
            echo ""
            echo "  pip       - 测速选择最佳 pip 镜像"
            echo "  npm       - 测速选择最佳 npm 镜像"
            echo "  termux    - 测速选择最佳 Termux pkg 镜像"
            echo "  docker    - 测速选择最佳 Docker 镜像"
            echo "  configure - 自动配置所有镜像源"
            echo "  all       - 测速并配置所有镜像源"
            ;;
    esac
fi
