#!/usr/bin/env python3
"""Linux System Monitoring Tool - Similar to htop"""

import time
import signal
import argparse
from datetime import datetime
import psutil
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

try:
    import boto3
    from botocore.exceptions import NoCredentialsError
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False


class SystemMonitor:
    def __init__(self, cloudwatch_enabled=False, cloudwatch_region='us-east-1', namespace='SystemMonitor'):
        self.console = Console()
        self.cloudwatch_enabled = cloudwatch_enabled and CLOUDWATCH_AVAILABLE
        self.running = True
        
        if self.cloudwatch_enabled:
            try:
                self.cloudwatch = boto3.client('cloudwatch', region_name=cloudwatch_region)
                self.namespace = namespace
                self.console.print(f"[green]CloudWatch enabled (region: {cloudwatch_region})[/green]")
            except (NoCredentialsError, Exception) as e:
                self.console.print(f"[yellow]CloudWatch disabled: {e}[/yellow]")
                self.cloudwatch_enabled = False
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        self.running = False
    
    def get_cpu_info(self):
        return {
            'total': psutil.cpu_percent(interval=0.1),
            'count': psutil.cpu_count(),
            'per_core': psutil.cpu_percent(interval=0.1, percpu=True),
            'frequency': psutil.cpu_freq().current if psutil.cpu_freq() else None
        }
    
    def get_memory_info(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            'total': mem.total, 'available': mem.available, 'used': mem.used, 'percent': mem.percent,
            'swap_total': swap.total, 'swap_used': swap.used, 'swap_percent': swap.percent
        }
    
    def get_disk_info(self):
        return [{
            'device': p.device, 'mountpoint': p.mountpoint, 'percent': psutil.disk_usage(p.mountpoint).percent,
            'used': psutil.disk_usage(p.mountpoint).used, 'total': psutil.disk_usage(p.mountpoint).total
        } for p in psutil.disk_partitions() if self._check_disk(p)]
    
    def _check_disk(self, partition):
        try:
            psutil.disk_usage(partition.mountpoint)
            return True
        except (PermissionError, OSError):
            return False
    
    def get_network_info(self):
        net_io = psutil.net_io_counters()
        try:
            connections = len(psutil.net_connections())
        except (psutil.AccessDenied, PermissionError):
            connections = 0
        return {
            'bytes_sent': net_io.bytes_sent, 'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent, 'packets_recv': net_io.packets_recv,
            'errin': net_io.errin, 'errout': net_io.errout,
            'connections': connections
        }
    
    def get_process_info(self, limit=10):
        processes = []
        for proc in psutil.process_iter():
            try:
                with proc.oneshot():
                    processes.append({
                        'pid': proc.pid, 'name': proc.name(),
                        'cpu_percent': proc.cpu_percent(interval=0) or 0.0,
                        'memory_percent': proc.memory_percent() or 0.0,
                        'status': proc.status()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, Exception):
                continue
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        return processes[:limit]
    
    def format_bytes(self, bytes_value):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def _bar(self, percent, length=50):
        filled = int(percent / (100 / length))
        return "█" * filled + "░" * (length - filled)
    
    def _color(self, value, thresholds=(50, 80)):
        return "green" if value < thresholds[0] else "yellow" if value < thresholds[1] else "red"
    
    def create_cpu_panel(self, cpu_info):
        table = Table(show_header=False, box=None, padding=(0, 1))
        cpu_percent = cpu_info['total']
        table.add_row("CPU Usage:", f"[bold]{cpu_percent:.1f}%[/bold]")
        table.add_row("Cores:", str(cpu_info['count']))
        if cpu_info['frequency']:
            table.add_row("Frequency:", f"{cpu_info['frequency']:.0f} MHz")
        table.add_row("", f"[{self._color(cpu_percent)}]{self._bar(cpu_percent)}[/{self._color(cpu_percent)}]")
        
        if len(cpu_info['per_core']) <= 8:
            table.add_row("", ""); table.add_row("Per Core:", "")
            for i, core in enumerate(cpu_info['per_core']):
                bar = "█" * int(core / 4) + "░" * (25 - int(core / 4))
                table.add_row(f"  Core {i}:", f"[{self._color(core)}]{core:5.1f}% {bar}[/{self._color(core)}]")
        return Panel(table, title="[bold cyan]CPU[/bold cyan]", border_style="cyan")
    
    def create_memory_panel(self, mem_info):
        table = Table(show_header=False, box=None, padding=(0, 1))
        mem_percent = mem_info['percent']
        table.add_row("Memory:", f"[bold]{mem_percent:.1f}%[/bold]")
        table.add_row("Used:", self.format_bytes(mem_info['used']))
        table.add_row("Available:", self.format_bytes(mem_info['available']))
        table.add_row("Total:", self.format_bytes(mem_info['total']))
        table.add_row("", f"[{self._color(mem_percent)}]{self._bar(mem_percent)}[/{self._color(mem_percent)}]")
        table.add_row("", ""); table.add_row("Swap:", f"{mem_info['swap_percent']:.1f}%")
        table.add_row("Swap Used:", self.format_bytes(mem_info['swap_used']))
        table.add_row("Swap Total:", self.format_bytes(mem_info['swap_total']))
        return Panel(table, title="[bold green]Memory[/bold green]", border_style="green")
    
    def create_disk_panel(self, disk_info):
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Device", style="cyan")
        table.add_column("Mount", style="magenta")
        table.add_column("Usage", justify="right")
        table.add_column("Used", justify="right")
        table.add_column("Total", justify="right")
        for disk in disk_info[:5]:
            usage = disk['percent']
            bar = "█" * int(usage / 5) + "░" * (20 - int(usage / 5))
            table.add_row(
                disk['device'], disk['mountpoint'],
                f"[{self._color(usage, (70, 90))}]{usage:5.1f}% {bar}[/{self._color(usage, (70, 90))}]",
                self.format_bytes(disk['used']), self.format_bytes(disk['total'])
            )
        return Panel(table, title="[bold yellow]Disk[/bold yellow]", border_style="yellow")
    
    def create_network_panel(self, net_info):
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("Bytes Sent:", f"[bold]{self.format_bytes(net_info['bytes_sent'])}[/bold]")
        table.add_row("Bytes Received:", f"[bold]{self.format_bytes(net_info['bytes_recv'])}[/bold]")
        table.add_row("Packets Sent:", f"{net_info['packets_sent']:,}")
        table.add_row("Packets Received:", f"{net_info['packets_recv']:,}")
        table.add_row("Errors In:", f"[red]{net_info['errin']:,}[/red]" if net_info['errin'] > 0 else f"{net_info['errin']:,}")
        table.add_row("Errors Out:", f"[red]{net_info['errout']:,}[/red]" if net_info['errout'] > 0 else f"{net_info['errout']:,}")
        table.add_row("Active Connections:", str(net_info['connections']))
        return Panel(table, title="[bold magenta]Network[/bold magenta]", border_style="magenta")
    
    def create_process_table(self, processes):
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("PID", style="cyan", width=8)
        table.add_column("Name", style="green", width=20)
        table.add_column("CPU %", justify="right", width=10)
        table.add_column("Memory %", justify="right", width=12)
        table.add_column("Status", width=10)
        for proc in processes:
            status_color = "green" if proc['status'] == "running" else "yellow"
            table.add_row(
                str(proc['pid']), proc['name'][:20],
                f"{proc['cpu_percent']:5.1f}%", f"{proc['memory_percent']:5.1f}%",
                f"[{status_color}]{proc['status']}[/{status_color}]"
            )
        return Panel(table, title="[bold blue]Top Processes[/bold blue]", border_style="blue")
    
    def send_to_cloudwatch(self, cpu_info, mem_info, disk_info, net_info):
        if not self.cloudwatch_enabled:
            return
        try:
            timestamp = datetime.utcnow()
            metrics = [
                {'MetricName': 'CPUUtilization', 'Value': cpu_info['total'], 'Unit': 'Percent', 'Timestamp': timestamp},
                {'MetricName': 'MemoryUtilization', 'Value': mem_info['percent'], 'Unit': 'Percent', 'Timestamp': timestamp},
                {'MetricName': 'NetworkBytesSent', 'Value': net_info['bytes_sent'], 'Unit': 'Bytes', 'Timestamp': timestamp},
                {'MetricName': 'NetworkBytesReceived', 'Value': net_info['bytes_recv'], 'Unit': 'Bytes', 'Timestamp': timestamp}
            ]
            for disk in disk_info:
                metrics.append({
                    'MetricName': 'DiskUtilization', 'Value': disk['percent'], 'Unit': 'Percent',
                    'Timestamp': timestamp, 'Dimensions': [
                        {'Name': 'Device', 'Value': disk['device']},
                        {'Name': 'MountPoint', 'Value': disk['mountpoint']}
                    ]
                })
            for i in range(0, len(metrics), 20):
                self.cloudwatch.put_metric_data(Namespace=self.namespace, MetricData=metrics[i:i+20])
        except Exception:
            pass
    
    def create_layout(self, cpu_info, mem_info, disk_info, net_info, processes):
        header_text = Text("Linux System Monitor", style="bold white on blue")
        header_text.append(f" | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        if self.cloudwatch_enabled:
            header_text.append(" | CloudWatch: ON", style="green")
        header = Panel(header_text, border_style="blue")
        footer = Panel(Text("Press Ctrl+C to exit", style="dim"), border_style="dim")
        
        layout = Layout()
        layout.split(Layout(header, name="header", size=3), Layout(name="main"), Layout(footer, name="footer", size=3))
        layout["main"].split_row(Layout(name="left"), Layout(name="right"))
        layout["left"].split(Layout(name="cpu_mem"), Layout(self.create_disk_panel(disk_info), name="disk"))
        layout["cpu_mem"].split_row(Layout(self.create_cpu_panel(cpu_info), name="cpu"), Layout(self.create_memory_panel(mem_info), name="mem"))
        layout["right"].split(Layout(self.create_network_panel(net_info), name="network"), Layout(self.create_process_table(processes), name="processes"))
        return layout
    
    def collect_metrics(self):
        def safe_get(func, default):
            try:
                return func()
            except Exception:
                return default
        
        return (
            safe_get(self.get_cpu_info, {'total': 0, 'count': 1, 'per_core': [0], 'frequency': None}),
            safe_get(self.get_memory_info, {'total': 0, 'available': 0, 'used': 0, 'percent': 0, 'swap_total': 0, 'swap_used': 0, 'swap_percent': 0}),
            safe_get(self.get_disk_info, []),
            safe_get(self.get_network_info, {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0, 'errin': 0, 'errout': 0, 'connections': 0}),
            safe_get(lambda: self.get_process_info(), [])
        )
    
    def run(self):
        cloudwatch_counter = 0
        cpu_info, mem_info, disk_info, net_info, processes = self.collect_metrics()
        initial_layout = self.create_layout(cpu_info, mem_info, disk_info, net_info, processes)
        
        with Live(initial_layout, console=self.console, refresh_per_second=2, screen=True) as live:
            while self.running:
                try:
                    cpu_info, mem_info, disk_info, net_info, processes = self.collect_metrics()
                    
                    if self.cloudwatch_enabled:
                        cloudwatch_counter += 1
                        if cloudwatch_counter >= 120:
                            self.send_to_cloudwatch(cpu_info, mem_info, disk_info, net_info)
                            cloudwatch_counter = 0
                    
                    live.update(self.create_layout(cpu_info, mem_info, disk_info, net_info, processes))
                    time.sleep(0.5)
                except KeyboardInterrupt:
                    break
                except Exception:
                    time.sleep(1)
        
        self.console.print("\n[green]Monitoring stopped.[/green]")


def main():
    parser = argparse.ArgumentParser(description="Linux System Monitoring Tool - Similar to htop")
    parser.add_argument('--cloudwatch', action='store_true', help='Enable CloudWatch metrics export')
    parser.add_argument('--region', default='us-east-1', help='AWS region for CloudWatch')
    parser.add_argument('--namespace', default='SystemMonitor', help='CloudWatch namespace')
    
    args = parser.parse_args()
    monitor = SystemMonitor(
        cloudwatch_enabled=args.cloudwatch,
        cloudwatch_region=args.region,
        namespace=args.namespace
    )
    monitor.run()


if __name__ == "__main__":
    main()
