import psutil
import time

# Function to display system metrics
def display_metrics():
    print(f"{'Metric':<30}{'Value'}")
    print(f"{'='*60}")
    print(f"{'CPU Usage (%)':<30}{psutil.cpu_percent(interval=1)}")
    print(f"{'Memory Usage (%)':<30}{psutil.virtual_memory().percent}")
    print(f"{'Disk Usage (%)':<30}{psutil.disk_usage('/').percent}")
    print(f"{'Network IO (bytes)':<30}{psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv}")
    print(f"{'Processes Count':<30}{len(psutil.pids())}")

# Continuously monitor system metrics
try:
    while True:
        display_metrics()
        time.sleep(5)
except KeyboardInterrupt:
    print("Monitoring stopped.")