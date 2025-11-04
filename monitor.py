#!/usr/bin/env python3
"""
Linux System Monitoring Tool
A CLI tool that monitors CPU, memory, network, and disk usage, similar to htop.
"""

import time
import sys
import signal
import argparse
from collections import deque
from datetime import datetime
import psutil
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

# CloudWatch integration (optional)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False


class SystemMonitor:
    """Main system monitoring class"""
    
    def __init__(self, cloudwatch_enabled=False, cloudwatch_region='us-east-1', namespace='SystemMonitor'):
        self.console = Console()
        self.cloudwatch_enabled = cloudwatch_enabled and CLOUDWATCH_AVAILABLE
        self.cloudwatch_region = cloudwatch_region
        self.namespace = namespace
        self.running = True
        self.cpu_history = deque(maxlen=50)
        self.mem_history = deque(maxlen=50)
        
        # CloudWatch client
        if self.cloudwatch_enabled:
            try:
                self.cloudwatch = boto3.client('cloudwatch', region_name=cloudwatch_region)
                self.console.print(f"[green]CloudWatch enabled (region: {cloudwatch_region})[/green]")
            except NoCredentialsError:
                self.console.print("[yellow]CloudWatch credentials not found. Continuing without CloudWatch.[/yellow]")
                self.cloudwatch_enabled = False
            except Exception as e:
                self.console.print(f"[yellow]CloudWatch initialization failed: {e}. Continuing without CloudWatch.[/yellow]")
                self.cloudwatch_enabled = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        self.running = False
    
    def get_cpu_info(self):
        """Get CPU usage information"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        
        self.cpu_history.append(cpu_percent)
        
        return {
            'total': cpu_percent,
            'count': cpu_count,
            'per_core': cpu_per_core,
            'frequency': cpu_freq.current if cpu_freq else None,
            'history': list(self.cpu_history)
        }
    
    def get_memory_info(self):
        """Get memory usage information"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        self.mem_history.append(mem.percent)
        
        return {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent,
            'history': list(self.mem_history)
        }
    
    def get_disk_info(self):
        """Get disk usage information"""
        disk_partitions = psutil.disk_partitions()
        disk_info = []
        
        for partition in disk_partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except PermissionError:
                continue
        
        return disk_info
    
    def get_network_info(self):
        """Get network usage information"""
        net_io = psutil.net_io_counters()
        try:
            net_connections = len(psutil.net_connections())
        except (psutil.AccessDenied, PermissionError):
            # May require elevated permissions on some systems
            net_connections = 0
        
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout,
            'connections': net_connections
        }
    
    def get_process_info(self, limit=10):
        """Get top processes by CPU usage"""
        processes = []
        try:
            # Collect process info with limited iterations for performance
            count = 0
            max_iterations = 200  # Limit iterations to avoid performance issues
            
            for proc in psutil.process_iter():
                if count >= max_iterations:
                    break
                count += 1
                
                try:
                    # Get process info with error handling
                    with proc.oneshot():
                        pid = proc.pid
                        name = proc.name()
                        # cpu_percent needs interval=0 for immediate result (or returns 0.0)
                        cpu_percent = proc.cpu_percent(interval=0)
                        memory_percent = proc.memory_percent()
                        status = proc.status()
                    
                    processes.append({
                        'pid': pid,
                        'name': name,
                        'cpu_percent': cpu_percent or 0.0,
                        'memory_percent': memory_percent or 0.0,
                        'status': status
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception:
                    # Skip processes that cause other errors
                    continue
        except Exception:
            # If process_iter fails entirely, return empty list
            return []
        
        # Sort by CPU usage
        processes.sort(key=lambda x: float(x.get('cpu_percent') or 0), reverse=True)
        return processes[:limit]
    
    def format_bytes(self, bytes_value):
        """Format bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def create_cpu_panel(self, cpu_info):
        """Create CPU usage panel"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        # Overall CPU
        cpu_percent = cpu_info['total']
        table.add_row("CPU Usage:", f"[bold]{cpu_percent:.1f}%[/bold]")
        table.add_row("Cores:", f"{cpu_info['count']}")
        
        if cpu_info['frequency']:
            table.add_row("Frequency:", f"{cpu_info['frequency']:.0f} MHz")
        
        # CPU bar
        bar_color = "green" if cpu_percent < 50 else "yellow" if cpu_percent < 80 else "red"
        cpu_bar = "█" * int(cpu_percent / 2) + "░" * (50 - int(cpu_percent / 2))
        table.add_row("", f"[{bar_color}]{cpu_bar}[/{bar_color}]")
        
        # Per-core CPU
        if len(cpu_info['per_core']) <= 8:
            table.add_row("", "")
            table.add_row("Per Core:", "")
            for i, core_percent in enumerate(cpu_info['per_core']):
                core_bar = "█" * int(core_percent / 4) + "░" * (25 - int(core_percent / 4))
                core_color = "green" if core_percent < 50 else "yellow" if core_percent < 80 else "red"
                table.add_row(f"  Core {i}:", f"[{core_color}]{core_percent:5.1f}% {core_bar}[/{core_color}]")
        
        return Panel(table, title="[bold cyan]CPU[/bold cyan]", border_style="cyan")
    
    def create_memory_panel(self, mem_info):
        """Create memory usage panel"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        mem_percent = mem_info['percent']
        table.add_row("Memory:", f"[bold]{mem_percent:.1f}%[/bold]")
        table.add_row("Used:", f"{self.format_bytes(mem_info['used'])}")
        table.add_row("Available:", f"{self.format_bytes(mem_info['available'])}")
        table.add_row("Total:", f"{self.format_bytes(mem_info['total'])}")
        
        # Memory bar
        bar_color = "green" if mem_percent < 50 else "yellow" if mem_percent < 80 else "red"
        mem_bar = "█" * int(mem_percent / 2) + "░" * (50 - int(mem_percent / 2))
        table.add_row("", f"[{bar_color}]{mem_bar}[/{bar_color}]")
        
        # Swap
        table.add_row("", "")
        table.add_row("Swap:", f"{mem_info['swap_percent']:.1f}%")
        table.add_row("Swap Used:", f"{self.format_bytes(mem_info['swap_used'])}")
        table.add_row("Swap Total:", f"{self.format_bytes(mem_info['swap_total'])}")
        
        return Panel(table, title="[bold green]Memory[/bold green]", border_style="green")
    
    def create_disk_panel(self, disk_info):
        """Create disk usage panel"""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Device", style="cyan")
        table.add_column("Mount", style="magenta")
        table.add_column("Usage", justify="right")
        table.add_column("Used", justify="right")
        table.add_column("Total", justify="right")
        
        for disk in disk_info[:5]:  # Show top 5 disks
            usage = disk['percent']
            bar_color = "green" if usage < 70 else "yellow" if usage < 90 else "red"
            bar = "█" * int(usage / 5) + "░" * (20 - int(usage / 5))
            
            table.add_row(
                disk['device'],
                disk['mountpoint'],
                f"[{bar_color}]{usage:5.1f}% {bar}[/{bar_color}]",
                self.format_bytes(disk['used']),
                self.format_bytes(disk['total'])
            )
        
        return Panel(table, title="[bold yellow]Disk[/bold yellow]", border_style="yellow")
    
    def create_network_panel(self, net_info):
        """Create network usage panel"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        
        table.add_row("Bytes Sent:", f"[bold]{self.format_bytes(net_info['bytes_sent'])}[/bold]")
        table.add_row("Bytes Received:", f"[bold]{self.format_bytes(net_info['bytes_recv'])}[/bold]")
        table.add_row("Packets Sent:", f"{net_info['packets_sent']:,}")
        table.add_row("Packets Received:", f"{net_info['packets_recv']:,}")
        table.add_row("Errors In:", f"[red]{net_info['errin']:,}[/red]" if net_info['errin'] > 0 else f"{net_info['errin']:,}")
        table.add_row("Errors Out:", f"[red]{net_info['errout']:,}[/red]" if net_info['errout'] > 0 else f"{net_info['errout']:,}")
        table.add_row("Active Connections:", f"{net_info['connections']}")
        
        return Panel(table, title="[bold magenta]Network[/bold magenta]", border_style="magenta")
    
    def create_process_table(self, processes):
        """Create top processes table"""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("PID", style="cyan", width=8)
        table.add_column("Name", style="green", width=20)
        table.add_column("CPU %", justify="right", width=10)
        table.add_column("Memory %", justify="right", width=12)
        table.add_column("Status", width=10)
        
        for proc in processes:
            cpu = proc['cpu_percent'] or 0
            mem = proc['memory_percent'] or 0
            status = proc['status']
            status_color = "green" if status == "running" else "yellow"
            
            table.add_row(
                str(proc['pid']),
                proc['name'][:20],
                f"{cpu:5.1f}%",
                f"{mem:5.1f}%",
                f"[{status_color}]{status}[/{status_color}]"
            )
        
        return Panel(table, title="[bold blue]Top Processes[/bold blue]", border_style="blue")
    
    def send_to_cloudwatch(self, cpu_info, mem_info, disk_info, net_info):
        """Send metrics to CloudWatch"""
        if not self.cloudwatch_enabled:
            return
        
        try:
            metrics = []
            timestamp = datetime.utcnow()
            
            # CPU metric
            metrics.append({
                'MetricName': 'CPUUtilization',
                'Value': cpu_info['total'],
                'Unit': 'Percent',
                'Timestamp': timestamp
            })
            
            # Memory metric
            metrics.append({
                'MetricName': 'MemoryUtilization',
                'Value': mem_info['percent'],
                'Unit': 'Percent',
                'Timestamp': timestamp
            })
            
            # Disk metrics
            for disk in disk_info:
                metrics.append({
                    'MetricName': 'DiskUtilization',
                    'Value': disk['percent'],
                    'Unit': 'Percent',
                    'Timestamp': timestamp,
                    'Dimensions': [
                        {'Name': 'Device', 'Value': disk['device']},
                        {'Name': 'MountPoint', 'Value': disk['mountpoint']}
                    ]
                })
            
            # Network metrics
            metrics.append({
                'MetricName': 'NetworkBytesSent',
                'Value': net_info['bytes_sent'],
                'Unit': 'Bytes',
                'Timestamp': timestamp
            })
            
            metrics.append({
                'MetricName': 'NetworkBytesReceived',
                'Value': net_info['bytes_recv'],
                'Unit': 'Bytes',
                'Timestamp': timestamp
            })
            
            # Send metrics in batches (CloudWatch limit is 20 metrics per request)
            for i in range(0, len(metrics), 20):
                batch = metrics[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
                
        except Exception as e:
            # Silently fail CloudWatch errors to not interrupt monitoring
            pass
    
    def create_layout(self, cpu_info, mem_info, disk_info, net_info, processes):
        """Create the main layout"""
        # Create header
        header_text = Text("Linux System Monitor", style="bold white on blue")
        header_text.append(f" | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        if self.cloudwatch_enabled:
            header_text.append(" | CloudWatch: ON", style="green")
        header_panel = Panel(header_text, border_style="blue")
        
        # Create footer
        footer_text = Text("Press Ctrl+C to exit", style="dim")
        footer_panel = Panel(footer_text, border_style="dim")
        
        # Create main content panels
        cpu_panel = self.create_cpu_panel(cpu_info)
        mem_panel = self.create_memory_panel(mem_info)
        disk_panel = self.create_disk_panel(disk_info)
        network_panel = self.create_network_panel(net_info)
        process_panel = self.create_process_table(processes)
        
        # Build layout structure - create empty layouts first
        layout = Layout()
        
        # Split into header, main, footer
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Assign header and footer
        layout["header"].update(header_panel)
        layout["footer"].update(footer_panel)
        
        # Split main into left and right
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Split left into cpu_mem and disk
        layout["left"].split(
            Layout(name="cpu_mem"),
            Layout(name="disk")
        )
        
        # Assign disk
        layout["disk"].update(disk_panel)
        
        # Split cpu_mem into cpu and mem
        layout["cpu_mem"].split_row(
            Layout(name="cpu"),
            Layout(name="mem")
        )
        
        # Assign cpu and mem
        layout["cpu"].update(cpu_panel)
        layout["mem"].update(mem_panel)
        
        # Split right into network and processes
        layout["right"].split(
            Layout(name="network"),
            Layout(name="processes")
        )
        
        # Assign network and processes
        layout["network"].update(network_panel)
        layout["processes"].update(process_panel)
        
        return layout
    
    def get_default_metrics(self):
        """Get default/fallback metrics"""
        return (
            {'total': 0, 'count': 1, 'per_core': [0], 'frequency': None, 'history': []},
            {'total': 0, 'available': 0, 'used': 0, 'percent': 0, 'swap_total': 0, 'swap_used': 0, 'swap_percent': 0, 'history': []},
            [],
            {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0, 'errin': 0, 'errout': 0, 'dropin': 0, 'dropout': 0, 'connections': 0},
            []
        )
    
    def collect_metrics(self):
        """Collect all system metrics with error handling"""
        # Collect metrics with individual error handling
        try:
            cpu_info = self.get_cpu_info()
        except Exception:
            cpu_info = {'total': 0, 'count': 1, 'per_core': [0], 'frequency': None, 'history': []}
        
        try:
            mem_info = self.get_memory_info()
        except Exception:
            mem_info = {'total': 0, 'available': 0, 'used': 0, 'percent': 0, 'swap_total': 0, 'swap_used': 0, 'swap_percent': 0, 'history': []}
        
        try:
            disk_info = self.get_disk_info()
        except Exception:
            disk_info = []
        
        try:
            net_info = self.get_network_info()
        except Exception:
            net_info = {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0, 'errin': 0, 'errout': 0, 'dropin': 0, 'dropout': 0, 'connections': 0}
        
        try:
            processes = self.get_process_info()
        except Exception:
            processes = []
        
        return cpu_info, mem_info, disk_info, net_info, processes
    
    def run(self):
        """Main monitoring loop"""
        cloudwatch_counter = 0
        
        # Create initial layout with default metrics
        cpu_info, mem_info, disk_info, net_info, processes = self.get_default_metrics()
        initial_layout = self.create_layout(cpu_info, mem_info, disk_info, net_info, processes)
        
        with Live(initial_layout, console=self.console, refresh_per_second=2, screen=True) as live:
            while self.running:
                try:
                    # Collect metrics
                    cpu_info, mem_info, disk_info, net_info, processes = self.collect_metrics()
                    
                    # Send to CloudWatch every 60 seconds (or every 120 updates at 2Hz)
                    if self.cloudwatch_enabled:
                        cloudwatch_counter += 1
                        if cloudwatch_counter >= 120:
                            try:
                                self.send_to_cloudwatch(cpu_info, mem_info, disk_info, net_info)
                            except Exception:
                                pass  # Don't break monitoring if CloudWatch fails
                            cloudwatch_counter = 0
                    
                    # Update display
                    try:
                        layout = self.create_layout(cpu_info, mem_info, disk_info, net_info, processes)
                        live.update(layout)
                    except Exception as layout_error:
                        # If layout fails, try a simpler fallback
                        try:
                            error_panel = Panel(f"Error: {str(layout_error)}", border_style="red")
                            live.update(error_panel)
                        except:
                            pass
                    
                    time.sleep(0.5)  # Update every 0.5 seconds
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    # Last resort error handling
                    time.sleep(1)
        
        self.console.print("\n[green]Monitoring stopped.[/green]")


def main():
    parser = argparse.ArgumentParser(
        description="Linux System Monitoring Tool - Similar to htop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor.py                    # Basic monitoring
  python monitor.py --cloudwatch       # Enable CloudWatch export
  python monitor.py --cloudwatch --region us-west-2  # Custom region
        """
    )
    
    parser.add_argument(
        '--cloudwatch',
        action='store_true',
        help='Enable CloudWatch metrics export (requires AWS credentials)'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region for CloudWatch (default: us-east-1)'
    )
    
    parser.add_argument(
        '--namespace',
        default='SystemMonitor',
        help='CloudWatch namespace (default: SystemMonitor)'
    )
    
    args = parser.parse_args()
    
    monitor = SystemMonitor(
        cloudwatch_enabled=args.cloudwatch,
        cloudwatch_region=args.region,
        namespace=args.namespace
    )
    
    monitor.run()


if __name__ == "__main__":
    main()

