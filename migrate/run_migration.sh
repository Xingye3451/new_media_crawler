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
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is not installed or not in PATH"
        exit 1
    fi
    
    # Check if required Python packages are installed
    if ! python3 -c "import mysql.connector, yaml" 2>/dev/null; then
        print_error "Required Python packages not found. Please install:"
        print_error "pip install mysql-connector-python pyyaml"
        exit 1
    fi
    
    # Check if migration script exists
    if [[ ! -f "$MIGRATION_SCRIPT" ]]; then
        print_error "Migration script not found: $MIGRATION_SCRIPT"
        exit 1
    fi
    
    # Check if config file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    # Check if VERSION file exists
    if [[ ! -f "$VERSION_FILE" ]]; then
        print_warning "VERSION file not found at $VERSION_FILE"
        print_warning "Creating default VERSION file with v1.0.0"
        echo "v1.0.0" > "$VERSION_FILE"
    fi
    
    print_success "Prerequisites check passed"
}

# Function to check database connection
check_database_connection() {
    print_info "Checking database connection..."
    
    if python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --check > /dev/null 2>&1; then
        print_success "Database connection successful"
    else
        print_error "Database connection failed. Please check your configuration."
        exit 1
    fi
}

# Function to create backup
create_backup() {
    if [[ "$CREATE_BACKUP" == true ]]; then
        print_info "Creating database backup..."
        
        # Create backup directory
        mkdir -p "$BACKUP_DIR"
        
        if python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --backup --backup-path "$BACKUP_DIR"; then
            print_success "Database backup created successfully"
        else
            print_error "Failed to create database backup"
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
    
    print_info "Starting migration..."
    print_info "Type: $MIGRATION_TYPE"
    print_info "Version: $MIGRATION_VERSION"
    print_info "Config: $CONFIG_FILE"
    
    # Build command
    CMD="python3 \"$MIGRATION_SCRIPT\" --config \"$CONFIG_FILE\" --type \"$MIGRATION_TYPE\" --version \"$MIGRATION_VERSION\""
    
    if [[ "$CREATE_BACKUP" == true ]]; then
        CMD="$CMD --backup --backup-path \"$BACKUP_DIR\""
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        CMD="$CMD --dry-run"
    fi
    
    # Execute migration
    print_info "Executing: $CMD"
    
    if eval "$CMD" 2>&1 | tee "$LOG_FILE"; then
        print_success "Migration completed successfully!"
        print_info "Log file: $LOG_FILE"
    else
        print_error "Migration failed!"
        print_info "Check log file for details: $LOG_FILE"
        exit 1
    fi
}

# Function to check database status
check_status() {
    print_info "Checking database status..."
    python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --check
}

# Function to show migration plan
show_migration_plan() {
    # Get version if not specified
    if [[ -z "$MIGRATION_VERSION" ]]; then
        MIGRATION_VERSION=$(get_project_version)
    fi
    
    print_info "Showing migration plan..."
    python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --type "$MIGRATION_TYPE" --version "$MIGRATION_VERSION" --dry-run
}

# Function to validate migration files
validate_migration_files() {
    # Get version if not specified
    if [[ -z "$MIGRATION_VERSION" ]]; then
        MIGRATION_VERSION=$(get_project_version)
    fi
    
    print_info "Validating migration files..."
    if python3 "$MIGRATION_SCRIPT" --config "$CONFIG_FILE" --type "$MIGRATION_TYPE" --version "$MIGRATION_VERSION" --validate; then
        print_success "Migration files validation passed"
    else
        print_error "Migration files validation failed"
        exit 1
    fi
}

# Function to get project version
get_project_version_info() {
    print_info "Getting project version..."
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
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_info "MediaCrawler Database Migration Script"
    print_info "====================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Handle different modes
    if [[ "$GET_VERSION" == true ]]; then
        get_project_version_info
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
    
    # Check database connection
    check_database_connection
    
    # Create backup if requested
    create_backup
    
    # Run migration
    run_migration
    
    print_success "Migration process completed!"
}

# Run main function
main "$@"
