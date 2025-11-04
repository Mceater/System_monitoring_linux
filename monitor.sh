#!/bin/bash
#
# System Monitoring Helper Scripts
# Provides various system monitoring utilities using native Linux commands
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to get CPU usage
get_cpu_usage() {
    echo "CPU Usage:"
    top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}'
    echo ""
    echo "Per-Core CPU Usage:"
    mpstat -P ALL 1 1 | awk '/^[0-9]/ {printf "CPU %s: %.1f%%\n", $2, 100-$NF}'
}

# Function to get memory usage
get_memory_usage() {
    echo "Memory Usage:"
    free -h
    echo ""
    echo "Memory Details:"
    cat /proc/meminfo | grep -E "MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree"
}

# Function to get disk usage
get_disk_usage() {
    echo "Disk Usage:"
    df -h
    echo ""
    echo "Disk I/O:"
    iostat -x 1 2 2>/dev/null || echo "iostat not available. Install sysstat package."
}

# Function to get network usage
get_network_usage() {
    echo "Network Interfaces:"
    ip -s link show 2>/dev/null || ifconfig
    echo ""
    echo "Network Statistics:"
    cat /proc/net/dev
    echo ""
    echo "Active Connections:"
    ss -tunap 2>/dev/null | head -20 || netstat -tunap 2>/dev/null | head -20
}

# Function to get top processes
get_top_processes() {
    echo "Top 10 CPU Processes:"
    ps aux --sort=-%cpu | head -11
    echo ""
    echo "Top 10 Memory Processes:"
    ps aux --sort=-%mem | head -11
}

# Function to monitor system load
get_system_load() {
    echo "System Load Average:"
    uptime
    echo ""
    echo "Load Average Details:"
    cat /proc/loadavg
}

# Function to get system information
get_system_info() {
    echo "System Information:"
    uname -a
    echo ""
    echo "Uptime:"
    uptime
    echo ""
    echo "CPU Information:"
    lscpu | grep -E "Model name|CPU\(s\)|Thread|Core|Socket"
}

# Function to continuously monitor (like watch)
continuous_monitor() {
    local interval=${1:-2}
    while true; do
        clear
        echo "=== System Monitor ==="
        date
        echo ""
        get_cpu_usage
        echo ""
        get_memory_usage
        echo ""
        get_disk_usage
        echo ""
        get_network_usage
        echo ""
        get_top_processes
        sleep "$interval"
    done
}

# Function to export metrics to a file
export_metrics() {
    local output_file=${1:-"system_metrics_$(date +%Y%m%d_%H%M%S).txt"}
    {
        echo "=== System Metrics Export ==="
        echo "Date: $(date)"
        echo ""
        get_system_info
        echo ""
        get_cpu_usage
        echo ""
        get_memory_usage
        echo ""
        get_disk_usage
        echo ""
        get_network_usage
        echo ""
        get_top_processes
    } > "$output_file"
    echo "Metrics exported to: $output_file"
}

# Main menu
show_menu() {
    echo -e "${BLUE}=== Linux System Monitor ===${NC}"
    echo "1. CPU Usage"
    echo "2. Memory Usage"
    echo "3. Disk Usage"
    echo "4. Network Usage"
    echo "5. Top Processes"
    echo "6. System Load"
    echo "7. System Information"
    echo "8. Continuous Monitor"
    echo "9. Export Metrics"
    echo "0. Exit"
    echo ""
    read -p "Select option: " option
    
    case $option in
        1) get_cpu_usage ;;
        2) get_memory_usage ;;
        3) get_disk_usage ;;
        4) get_network_usage ;;
        5) get_top_processes ;;
        6) get_system_load ;;
        7) get_system_info ;;
        8) read -p "Update interval (seconds, default 2): " interval; continuous_monitor "${interval:-2}" ;;
        9) read -p "Output file (default: auto-generated): " file; export_metrics "$file" ;;
        0) exit 0 ;;
        *) echo "Invalid option" ;;
    esac
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Script is being executed
    if [ $# -eq 0 ]; then
        # No arguments, show menu
        show_menu
    else
        # Arguments provided, execute specific function
        case "$1" in
            cpu) get_cpu_usage ;;
            memory|mem) get_memory_usage ;;
            disk) get_disk_usage ;;
            network|net) get_network_usage ;;
            processes|procs) get_top_processes ;;
            load) get_system_load ;;
            info) get_system_info ;;
            monitor|watch) continuous_monitor "${2:-2}" ;;
            export) export_metrics "$2" ;;
            *) echo "Usage: $0 [cpu|memory|disk|network|processes|load|info|monitor|export]"; exit 1 ;;
        esac
    fi
fi

