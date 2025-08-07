#!/bin/bash

# MediaCrawler Database Migration Script
# Version: v1.0.0
# Description: One-click database migration script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/config/config_local.yaml"
MIGRATION_SCRIPT="${SCRIPT_DIR}/migrate.py"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_FILE="${SCRIPT_DIR}/migration_$(date +%Y%m%d_%H%M%S).log"
VERSION_FILE="${PROJECT_ROOT}/VERSION"

# Default values
MIGRATION_TYPE="full"
MIGRATION_VERSION=""
CREATE_BACKUP=true
DRY_RUN=false
CHECK_STATUS=false
VALIDATE_FILES=false
GET_VERSION=false
ROLLBACK_VERSION=""
SHOW_HISTORY=false

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
        print_warning "VERSION file not found, using default version v1.0.0"
        echo "v1.0.0"
    fi
}

# Function to show usage
show_usage() {
    echo "MediaCrawler Database Migration Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE        Migration type (full/incremental) [default: full]"
    echo "  -v, --version VERSION  Migration version [default: read from VERSION file]"
    echo "  -c, --config FILE      Configuration file path [default: config/config_local.yaml]"
    echo "  -b, --backup           Create backup before migration [default: true]"
    echo "  -n, --no-backup        Skip backup creation"
    echo "  -d, --dry-run          Dry run (show what would be executed)"
    echo "  -s, --status           Check database status only"
    echo "  -V, --validate         Validate migration files"
    echo "  -g, --get-version      Get current project version"
    echo "  -r, --rollback VERSION Rollback to specified version"
    echo "  -H, --history          Show migration history"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run full migration with backup"
    echo "  $0 -t incremental -v v1.0.1          # Run incremental migration v1.0.1"
    echo "  $0 -d                                 # Dry run to see migration plan"
    echo "  $0 -s                                 # Check database status"
    echo "  $0 -n                                 # Run migration without backup"
    echo "  $0 -V                                 # Validate migration files"
    echo "  $0 -g                                 # Get current project version"
    echo "  $0 -r v1.0.0                         # Rollback to v1.0.0"
    echo "  $0 -H                                 # Show migration history"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "检查迁移环境..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装或不在 PATH 中"
        exit 1
    fi
    
    # Check if required Python packages are installed
    if ! python3 -c "import mysql.connector, yaml" 2>/dev/null; then
        print_error "缺少必要的 Python 包，请安装:"
        print_error "pip install mysql-connector-python pyyaml"
        exit 1
    fi
    
    # Check if VERSION file exists
    if [[ ! -f "$VERSION_FILE" ]]; then
        print_error "VERSION 文件不存在: $VERSION_FILE"
        exit 1
    fi
    
    # Check if migration script exists
    if [[ ! -f "$MIGRATION_SCRIPT" ]]; then
        print_error "迁移脚本不存在: $MIGRATION_SCRIPT"
        exit 1
    fi
    
    # Check if config file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        exit 1
    fi
    
    print_success "迁移环境检查通过"
}

# Function to check database connection
check_database_connection() {
    print_info "检查数据库连接..."
    
    if python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --check > /dev/null 2>&1; then
        print_success "数据库连接成功"
    else
        print_error "数据库连接失败，请检查配置"
        exit 1
    fi
}

# Function to create backup
create_backup() {
    if [[ "$CREATE_BACKUP" == true ]]; then
        print_info "创建数据库备份..."
        
        # Create backup directory
        mkdir -p "$BACKUP_DIR"
        
        if python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --backup --backup-path "$BACKUP_DIR"; then
            print_success "数据库备份创建成功"
        else
            print_error "创建数据库备份失败"
            exit 1
        fi
    fi
}

# Function to run migration
run_migration() {
    # Get version if not specified
    if [[ -z "$MIGRATION_VERSION" ]]; then
        MIGRATION_VERSION=$(get_project_version)
    fi
    
    print_info "开始迁移..."
    print_info "类型: $MIGRATION_TYPE"
    print_info "版本: $MIGRATION_VERSION"
    print_info "配置: $CONFIG_FILE"
    
    # Build command
    CMD="python3 \"$MIGRATION_SCRIPT\" --config \"$CONFIG_FILE\" --type \"$MIGRATION_TYPE\" --version \"$MIGRATION_VERSION\""
    
    if [[ "$CREATE_BACKUP" == true ]]; then
        CMD="$CMD --backup --backup-path \"$BACKUP_DIR\""
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        CMD="$CMD --dry-run"
    fi
    
    # Execute migration
    print_info "执行: $CMD"
    
    if eval "$CMD" 2>&1 | tee "$LOG_FILE"; then
        print_success "迁移完成!"
        print_info "日志文件: $LOG_FILE"
    else
        print_error "迁移失败!"
        print_info "检查日志文件: $LOG_FILE"
        exit 1
    fi
}

# Function to rollback migration
rollback_migration() {
    local target_version=$1
    
    print_info "开始回滚迁移..."
    print_info "目标版本: $target_version"
    
    # Build rollback command
    CMD="python3 \"$MIGRATION_SCRIPT\" --config \"$CONFIG_FILE\" --rollback \"$target_version\""
    
    # Execute rollback
    print_info "执行: $CMD"
    
    if eval "$CMD" 2>&1 | tee "$LOG_FILE"; then
        print_success "回滚完成!"
        print_info "日志文件: $LOG_FILE"
    else
        print_error "回滚失败!"
        print_info "检查日志文件: $LOG_FILE"
        exit 1
    fi
}

# Function to show migration history
show_migration_history() {
    print_info "显示迁移历史..."
    
    CMD="python3 \"$MIGRATION_SCRIPT\" --config \"$CONFIG_FILE\" --history"
    
    if eval "$CMD"; then
        print_success "迁移历史显示完成"
    else
        print_error "显示迁移历史失败"
        exit 1
    fi
}

# Function to check database status
check_status() {
    print_info "检查数据库状态..."
    python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --check
}

# Function to show migration plan
show_migration_plan() {
    # Get version if not specified
    if [[ -z "$MIGRATION_VERSION" ]]; then
        MIGRATION_VERSION=$(get_project_version)
    fi
    
    print_info "显示迁移计划..."
    python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --type "$MIGRATION_TYPE" --version "$MIGRATION_VERSION" --dry-run
}

# Function to validate migration files
validate_migration_files() {
    # Get version if not specified
    if [[ -z "$MIGRATION_VERSION" ]]; then
        MIGRATION_VERSION=$(get_project_version)
    fi
    
    print_info "验证迁移文件..."
    if python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --type "$MIGRATION_TYPE" --version "$MIGRATION_VERSION" --validate; then
        print_success "迁移文件验证通过"
    else
        print_error "迁移文件验证失败"
        exit 1
    fi
}

# Function to get project version
get_project_version_info() {
    print_info "获取项目版本..."
    python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --get-version
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            MIGRATION_TYPE="$2"
            shift 2
            ;;
        -v|--version)
            MIGRATION_VERSION="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        -n|--no-backup)
            CREATE_BACKUP=false
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -s|--status)
            CHECK_STATUS=true
            shift
            ;;
        -V|--validate)
            VALIDATE_FILES=true
            shift
            ;;
        -g|--get-version)
            GET_VERSION=true
            shift
            ;;
        -r|--rollback)
            ROLLBACK_VERSION="$2"
            shift 2
            ;;
        -H|--history)
            SHOW_HISTORY=true
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
    print_info "MediaCrawler 数据库迁移脚本"
    print_info "============================="
    
    # Check prerequisites
    check_prerequisites
    
    # Handle different modes
    if [[ "$GET_VERSION" == true ]]; then
        get_project_version_info
        exit 0
    fi
    
    if [[ "$SHOW_HISTORY" == true ]]; then
        show_migration_history
        exit 0
    fi
    
    if [[ "$CHECK_STATUS" == true ]]; then
        check_status
        exit 0
    fi
    
    if [[ "$VALIDATE_FILES" == true ]]; then
        validate_migration_files
        exit 0
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        show_migration_plan
        exit 0
    fi
    
    if [[ -n "$ROLLBACK_VERSION" ]]; then
        rollback_migration "$ROLLBACK_VERSION"
        exit 0
    fi
    
    # Check database connection
    check_database_connection
    
    # Create backup if requested
    create_backup
    
    # Run migration
    run_migration
    
    print_success "迁移流程完成!"
}

# Run main function
main "$@"
