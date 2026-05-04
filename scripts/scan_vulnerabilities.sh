#!/bin/bash

# SOAR Ransomware Lab - Vulnerability Scanner
# Scans Docker images for security vulnerabilities

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $*"
}

# Check if Trivy is installed
check_trivy() {
    if ! command -v trivy &> /dev/null; then
        warn "Trivy not found. Installing..."
        case "$(uname -s)" in
            Linux)
                if command -v apt-get &> /dev/null; then
                    sudo apt-get update
                    sudo apt-get install wget apt-transport-https gnupg lsb-release
                    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
                    echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
                    sudo apt-get update
                    sudo apt-get install trivy
                elif command -v yum &> /dev/null; then
                    sudo yum install -y https://github.com/aquasecurity/trivy/releases/latest/download/trivy_0.44.1_Linux-64bit.rpm
                else
                    error "Unsupported package manager. Please install Trivy manually."
                    exit 1
                fi
                ;;
            Darwin)
                if command -v brew &> /dev/null; then
                    brew install trivy
                else
                    error "Homebrew not found. Please install Trivy manually."
                    exit 1
                fi
                ;;
            *)
                error "Unsupported OS. Please install Trivy manually."
                exit 1
                ;;
        esac
    fi
}

# Get Docker images from docker-compose.yml
get_docker_images() {
    local compose_file="docker/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        error "docker-compose.yml not found in docker/ directory"
        exit 1
    fi
    
    # Extract image names from docker-compose.yml
    grep -E "^\s*image:" "$compose_file" | sed 's/.*image:\s*//' | sed 's/\${[^}]*}//g' | sort -u
}

# Scan single image
scan_image() {
    local image="$1"
    local report_dir="reports/vulnerability"
    local report_file="${report_dir}/$(echo "$image" | tr '/:' '_').json"
    
    mkdir -p "$report_dir"
    
    log "Scanning image: $image"
    
    if trivy image --format json --output "$report_file" "$image"; then
        # Check for critical/high vulnerabilities
        local critical=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' "$report_file" | wc -l)
        local high=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH") | .VulnerabilityID' "$report_file" | wc -l)
        local medium=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM") | .VulnerabilityID' "$report_file" | wc -l)
        local low=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW") | .VulnerabilityID' "$report_file" | wc -l)
        
        if [[ $critical -gt 0 ]]; then
            error "Found $critical CRITICAL vulnerabilities in $image"
        elif [[ $high -gt 0 ]]; then
            warn "Found $high HIGH vulnerabilities in $image"
        elif [[ $medium -gt 0 ]]; then
            info "Found $medium MEDIUM vulnerabilities in $image"
        else
            log "No significant vulnerabilities found in $image"
        fi
        
        return 0
    else
        error "Failed to scan $image"
        return 1
    fi
}

# Generate summary report
generate_summary() {
    local report_dir="reports/vulnerability"
    local summary_file="${report_dir}/summary.md"
    
    mkdir -p "$report_dir"
    
    cat > "$summary_file" << EOF
# Vulnerability Scan Summary

**Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Scanner:** Trivy

## Images Scanned

EOF
    
    local total_critical=0
    local total_high=0
    local total_medium=0
    local total_low=0
    
    for report_file in "${report_dir}"/*.json; do
        if [[ -f "$report_file" ]]; then
            local image=$(basename "$report_file" .json | tr '_' ':' | tr '_' '/')
            local critical=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' "$report_file" 2>/dev/null | wc -l || echo 0)
            local high=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH") | .VulnerabilityID' "$report_file" 2>/dev/null | wc -l || echo 0)
            local medium=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "MEDIUM") | .VulnerabilityID' "$report_file" 2>/dev/null | wc -l || echo 0)
            local low=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "LOW") | .VulnerabilityID' "$report_file" 2>/dev/null | wc -l || echo 0)
            
            echo "- **$image**: CRITICAL: $critical, HIGH: $high, MEDIUM: $medium, LOW: $low" >> "$summary_file"
            
            total_critical=$((total_critical + critical))
            total_high=$((total_high + high))
            total_medium=$((total_medium + medium))
            total_low=$((total_low + low))
        fi
    done
    
    cat >> "$summary_file" << EOF

## Summary

- **Total CRITICAL:** $total_critical
- **Total HIGH:** $total_high  
- **Total MEDIUM:** $total_medium
- **Total LOW:** $total_low

## Recommendations

EOF
    
    if [[ $total_critical -gt 0 ]]; then
        echo "- 🚨 **URGENT**: Update images with CRITICAL vulnerabilities immediately" >> "$summary_file"
    fi
    
    if [[ $total_high -gt 0 ]]; then
        echo "- ⚠️ **HIGH PRIORITY**: Plan updates for images with HIGH vulnerabilities" >> "$summary_file"
    fi
    
    if [[ $total_medium -gt 0 ]]; then
        echo "- 📋 **MEDIUM**: Consider updating images with MEDIUM vulnerabilities in next cycle" >> "$summary_file"
    fi
    
    if [[ $total_critical -eq 0 && $total_high -eq 0 ]]; then
        echo "- ✅ **GOOD**: No critical or high vulnerabilities found" >> "$summary_file"
    fi
    
    log "Summary report generated: $summary_file"
}

# Main function
main() {
    log "Starting vulnerability scan for SOAR Ransomware Lab images..."
    
    # Check/install Trivy
    check_trivy
    
    # Get Docker images
    local images
    readarray -t images < <(get_docker_images)
    
    if [[ ${#images[@]} -eq 0 ]]; then
        error "No Docker images found in docker-compose.yml"
        exit 1
    fi
    
    log "Found ${#images[@]} images to scan"
    
    # Scan each image
    local failed_scans=0
    for image in "${images[@]}"; do
        if ! scan_image "$image"; then
            failed_scans=$((failed_scans + 1))
        fi
    done
    
    # Generate summary
    generate_summary
    
    # Final status
    if [[ $failed_scans -gt 0 ]]; then
        error "$failed_scans scans failed. Check reports for details."
        exit 1
    else
        log "All vulnerability scans completed successfully"
    fi
}

# Help function
show_help() {
    cat << EOF
SOAR Ransomware Lab - Vulnerability Scanner

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -h, --help      Show this help message
    -i, --image     Scan specific image only
    -r, --report-dir Directory for reports (default: reports/vulnerability)

EXAMPLES:
    $0                          # Scan all images from docker-compose.yml
    $0 -i nginx:latest          # Scan specific image
    $0 -r /tmp/scan-reports    # Use custom report directory

REQUIREMENTS:
    - Trivy vulnerability scanner (will be installed if missing)
    - Docker daemon running
    - jq for JSON processing

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--image)
            SINGLE_IMAGE="$2"
            shift 2
            ;;
        -r|--report-dir)
            REPORT_DIR="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Override report directory if specified
if [[ -n "${REPORT_DIR:-}" ]]; then
    mkdir -p "$REPORT_DIR"
    export REPORT_DIR
fi

# Run main function or scan single image
if [[ -n "${SINGLE_IMAGE:-}" ]]; then
    check_trivy
    scan_image "$SINGLE_IMAGE"
else
    main
fi
