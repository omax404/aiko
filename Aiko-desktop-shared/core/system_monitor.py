"""
AIKO SYSTEM MONITOR
Monitors system health: CPU, RAM, GPU usage.
"""

import asyncio


class SystemMonitor:
    """System health monitoring for the dashboard."""
    
    def __init__(self):
        self.cpu_percent = 0.0
        self.ram_percent = 0.0
        self.ram_used_gb = 0.0
        self.ram_total_gb = 12.0
        self.gpu_percent = 0.0
        self.gpu_memory_gb = 0.0
        
    def update(self):
        """Update all system stats."""
        try:
            import psutil
            
            self.cpu_percent = psutil.cpu_percent(interval=0.1)
            
            mem = psutil.virtual_memory()
            self.ram_percent = mem.percent
            self.ram_used_gb = mem.used / (1024 ** 3)
            self.ram_total_gb = mem.total / (1024 ** 3)
            
        except ImportError:
            print("⚠️ psutil not installed")
            
        # GPU monitoring (NVIDIA)
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                self.gpu_percent = gpu.load * 100
                self.gpu_memory_gb = gpu.memoryUsed / 1024
        except Exception:
            pass
            
    def get_stats(self) -> dict:
        """Get current stats."""
        self.update()
        return {
            "cpu": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_used": self.ram_used_gb,
            "ram_total": self.ram_total_gb,
            "gpu": self.gpu_percent,
            "gpu_memory": self.gpu_memory_gb,
        }
        
    def get_health_status(self) -> str:
        """Get overall health status."""
        self.update()
        
        if self.cpu_percent > 90 or self.ram_percent > 90:
            return "critical"
        elif self.cpu_percent > 70 or self.ram_percent > 70:
            return "warning"
        else:
            return "healthy"
