# Linux System Monitoring Tool

A comprehensive CLI tool that monitors CPU, memory, network, and disk usage, similar to `htop`. Built with Python and Bash, featuring an interactive terminal UI and optional CloudWatch integration.

## Features

- **Real-time System Monitoring**
  - CPU usage (overall and per-core)
  - Memory usage (RAM and swap)
  - Disk usage and I/O statistics
  - Network traffic and connections
  - Top processes by CPU and memory usage

- **Interactive Terminal UI**
  - Beautiful, color-coded interface using Rich library
  - Live updating display (2 updates per second)
  - Visual progress bars for resource usage
  - Organized panels for different metrics

- **CloudWatch Integration** (Stretch Goal)
  - Export metrics to AWS CloudWatch
  - Automatic batching of metrics
  - Configurable namespace and region
  - Sends metrics every 60 seconds

- **Bash Helper Scripts**
  - Additional system monitoring utilities
  - Command-line interface for quick checks
  - Continuous monitoring mode
  - Metrics export functionality

## Requirements

- Python 3.7+
- Linux system (or macOS for testing)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone or download this repository:
   ```bash
   cd system-monitor
   ```

2. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   # Or use: python3 -m pip install -r requirements.txt
   ```

3. Make scripts executable:
   ```bash
   chmod +x monitor.py monitor.sh cloudwatch_setup.sh
   ```

## Usage

### Basic Monitoring

Run the main monitoring tool:
```bash
python monitor.py
```

This will start an interactive terminal UI showing:
- CPU usage with per-core breakdown
- Memory and swap usage
- Disk usage for all mounted partitions
- Network statistics
- Top 10 processes by CPU usage

Press `Ctrl+C` to exit.

### CloudWatch Integration

1. **Setup AWS Credentials** (if not already configured):
   ```bash
   ./cloudwatch_setup.sh
   ```
   Or manually:
   ```bash
   aws configure
   ```

2. **Run with CloudWatch enabled**:
   ```bash
   python monitor.py --cloudwatch
   ```

3. **Custom region and namespace**:
   ```bash
   python monitor.py --cloudwatch --region us-west-2 --namespace MySystemMonitor
   ```

### Bash Helper Script

The `monitor.sh` script provides additional system monitoring capabilities:

```bash
# Interactive menu
./monitor.sh

# Specific metrics
./monitor.sh cpu
./monitor.sh memory
./monitor.sh disk
./monitor.sh network
./monitor.sh processes

# Continuous monitoring (like watch)
./monitor.sh monitor 2  # Update every 2 seconds

# Export metrics to file
./monitor.sh export metrics.txt
```

## Command Line Options

### Python Monitor (`monitor.py`)

```
--cloudwatch          Enable CloudWatch metrics export
--region REGION       AWS region for CloudWatch (default: us-east-1)
--namespace NAME      CloudWatch namespace (default: SystemMonitor)
```

### Bash Monitor (`monitor.sh`)

```
Usage: ./monitor.sh [command] [options]

Commands:
  cpu          Show CPU usage
  memory       Show memory usage
  disk         Show disk usage
  network      Show network statistics
  processes    Show top processes
  load         Show system load
  info         Show system information
  monitor      Continuous monitoring mode
  export       Export metrics to file
```

## CloudWatch Metrics

When CloudWatch is enabled, the following metrics are exported:

- **CPUUtilization** - Overall CPU usage percentage
- **MemoryUtilization** - Memory usage percentage
- **DiskUtilization** - Disk usage per device/mountpoint
- **NetworkBytesSent** - Total bytes sent
- **NetworkBytesReceived** - Total bytes received

Metrics are sent every 60 seconds to minimize CloudWatch API calls and costs.

## Project Structure

```
system-monitor/
├── monitor.py              # Main Python monitoring application
├── monitor.sh              # Bash helper scripts
├── cloudwatch_setup.sh     # CloudWatch setup utility
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Technical Details

### System Calls and Process Management

The tool uses the `psutil` library which provides:
- Cross-platform system and process utilities
- Low-level system information access
- Efficient process iteration and filtering

### Performance Monitoring

- Updates every 0.5 seconds (2 Hz)
- Maintains history of CPU and memory usage
- Efficient data collection with minimal overhead
- Non-blocking CloudWatch operations

### AWS SDK Integration

- Uses `boto3` for CloudWatch API calls
- Handles credential errors gracefully
- Batches metrics to respect CloudWatch limits (20 metrics per request)
- Continues monitoring even if CloudWatch fails

## Skills Demonstrated

- ✅ System calls and process management (psutil)
- ✅ Scripting (Bash scripts for system utilities)
- ✅ Performance monitoring (real-time metrics collection)
- ✅ AWS SDK usage (boto3 for CloudWatch)
- ✅ CLI tool development (argparse, Rich TUI)
- ✅ Error handling and graceful degradation

## Troubleshooting

### Permission Errors

Some system information may require elevated permissions:
```bash
sudo python monitor.py
```

### CloudWatch Errors

If CloudWatch export fails:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify IAM permissions for CloudWatch
3. Check network connectivity
4. The monitor will continue without CloudWatch

### Missing Dependencies

Install missing system packages:
```bash
# Ubuntu/Debian
sudo apt-get install sysstat

# RHEL/CentOS
sudo yum install sysstat

# macOS
brew install sysstat
```

## License

This project is provided as-is for educational and demonstration purposes.

## Future Enhancements

- [ ] Process filtering and search
- [ ] Historical data graphs
- [ ] Customizable refresh rate
- [ ] Alert thresholds
- [ ] Multiple machine monitoring
- [ ] Export to other monitoring systems (Prometheus, Grafana)

