#!/bin/bash

# MediaCrawler Docker 构建脚本
# 自动读取 VERSION 文件并构建对应版本的镜像

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="${SCRIPT_DIR}/VERSION"
DOCKERFILE="${SCRIPT_DIR}/prod.Dockerfile"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get project version
get_project_version() {
    if [[ -f "$VERSION_FILE" ]]; then
        cat "$VERSION_FILE" | tr -d '\n'
    else
        print_error "VERSION file not found at $VERSION_FILE"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "MediaCrawler Docker 构建脚本"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -v, --version VERSION 指定版本号 [默认: 读取 VERSION 文件]"
    echo "  -t, --tag TAG         指定镜像标签 [默认: mediacrawler-api:VERSION]"
    echo "  -p, --push            构建完成后推送到镜像仓库"
    echo "  -r, --registry REGISTRY 指定镜像仓库地址"
    echo "  -c, --compose         同时启动 docker-compose"
    echo "  -s, --stop            停止并删除现有容器"
    echo "  -l, --latest          同时标记为 latest 标签"
    echo "  -h, --help            显示帮助信息"
    echo ""
    echo "Examples:"
    echo "  $0                                    # 使用 VERSION 文件构建"
    echo "  $0 -v v1.0.1                         # 指定版本构建"
    echo "  $0 -p -r myregistry.com              # 构建并推送到指定仓库"
    echo "  $0 -c                                 # 构建并启动容器"
    echo "  $0 -s -c                             # 停止现有容器，构建并启动新容器"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "检查构建环境..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装或不在 PATH 中"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装或不在 PATH 中"
        exit 1
    fi
    
    # Check if VERSION file exists
    if [[ ! -f "$VERSION_FILE" ]]; then
        print_error "VERSION 文件不存在: $VERSION_FILE"
        exit 1
    fi
    
    # Check if Dockerfile exists
    if [[ ! -f "$DOCKERFILE" ]]; then
        print_error "Dockerfile 不存在: $DOCKERFILE"
        exit 1
    fi
    
    # Check if docker-compose.yml exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        print_error "docker-compose.yml 不存在: $COMPOSE_FILE"
        exit 1
    fi
    
    print_success "构建环境检查通过"
}

# Function to build Docker image
build_image() {
    local version=$1
    local tag=$2
    local registry=$3
    
    print_info "开始构建 Docker 镜像..."
    print_info "版本: $version"
    print_info "标签: $tag"
    
    # Get build arguments
    local build_date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    local vcs_ref=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    # Build command
    local build_cmd="docker build"
    build_cmd="$build_cmd --build-arg VERSION=$version"
    build_cmd="$build_cmd --build-arg BUILD_DATE=$build_date"
    build_cmd="$build_cmd --build-arg VCS_REF=$vcs_ref"
    build_cmd="$build_cmd -t $tag"
    
    if [[ -n "$registry" ]]; then
        local registry_tag="$registry/$tag"
        build_cmd="$build_cmd -t $registry_tag"
    fi
    
    build_cmd="$build_cmd -f $DOCKERFILE ."
    
    print_info "执行构建命令: $build_cmd"
    
    if eval "$build_cmd"; then
        print_success "Docker 镜像构建成功!"
        
        # Show image info
        print_info "镜像信息:"
        docker images | grep "$(echo $tag | cut -d: -f1)"
        
        return 0
    else
        print_error "Docker 镜像构建失败!"
        return 1
    fi
}

# Function to push image
push_image() {
    local tag=$1
    local registry=$2
    
    if [[ -n "$registry" ]]; then
        local registry_tag="$registry/$tag"
        print_info "推送镜像到仓库: $registry_tag"
        
        if docker push "$registry_tag"; then
            print_success "镜像推送成功!"
        else
            print_error "镜像推送失败!"
            return 1
        fi
    else
        print_warning "未指定镜像仓库，跳过推送"
    fi
}

# Function to stop containers
stop_containers() {
    print_info "停止现有容器..."
    
    if docker-compose -f "$COMPOSE_FILE" down; then
        print_success "容器已停止"
    else
        print_warning "停止容器时出现警告"
    fi
}

# Function to start containers
start_containers() {
    local version=$1
    
    print_info "启动容器..."
    print_info "使用版本: $version"
    
    # Set environment variable for docker-compose
    export VERSION="$version"
    
    if docker-compose -f "$COMPOSE_FILE" up -d; then
        print_success "容器启动成功!"
        
        # Show container status
        print_info "容器状态:"
        docker-compose -f "$COMPOSE_FILE" ps
        
        # Show access information
        print_info "访问信息:"
        echo "  API 服务: http://localhost:8100"
        echo "  VNC Web界面: http://localhost:6080"
        echo "  VNC 直连: localhost:5901"
        
    else
        print_error "容器启动失败!"
        return 1
    fi
}

# Function to tag as latest
tag_latest() {
    local tag=$1
    local registry=$2
    
    print_info "标记为 latest 版本..."
    
    local latest_tag="${tag%:*}:latest"
    if docker tag "$tag" "$latest_tag"; then
        print_success "标记为 latest 成功: $latest_tag"
    else
        print_error "标记为 latest 失败!"
        return 1
    fi
    
    if [[ -n "$registry" ]]; then
        local registry_latest="$registry/$latest_tag"
        if docker tag "$tag" "$registry_latest"; then
            print_success "标记为 latest 成功: $registry_latest"
        else
            print_error "标记为 latest 失败!"
            return 1
        fi
    fi
}

# Parse command line arguments
VERSION=""
TAG=""
PUSH=false
REGISTRY=""
COMPOSE=false
STOP=false
LATEST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -c|--compose)
            COMPOSE=true
            shift
            ;;
        -s|--stop)
            STOP=true
            shift
            ;;
        -l|--latest)
            LATEST=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_info "MediaCrawler Docker 构建脚本"
    print_info "============================="
    
    # Check prerequisites
    check_prerequisites
    
    # Get version if not specified
    if [[ -z "$VERSION" ]]; then
        VERSION=$(get_project_version)
    fi
    
    # Set tag if not specified
    if [[ -z "$TAG" ]]; then
        TAG="mediacrawler-api:$VERSION"
    fi
    
    print_info "构建配置:"
    print_info "  版本: $VERSION"
    print_info "  标签: $TAG"
    print_info "  推送: $PUSH"
    print_info "  仓库: ${REGISTRY:-未指定}"
    print_info "  启动容器: $COMPOSE"
    print_info "  停止现有: $STOP"
    print_info "  标记latest: $LATEST"
    
    # Stop containers if requested
    if [[ "$STOP" == true ]]; then
        stop_containers
    fi
    
    # Build image
    if build_image "$VERSION" "$TAG" "$REGISTRY"; then
        
        # Tag as latest if requested
        if [[ "$LATEST" == true ]]; then
            tag_latest "$TAG" "$REGISTRY"
        fi
        
        # Push image if requested
        if [[ "$PUSH" == true ]]; then
            push_image "$TAG" "$REGISTRY"
        fi
        
        # Start containers if requested
        if [[ "$COMPOSE" == true ]]; then
            start_containers "$VERSION"
        fi
        
        print_success "构建流程完成!"
        
    else
        print_error "构建流程失败!"
        exit 1
    fi
}

# Run main function
main "$@"
