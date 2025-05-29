#!/usr/bin/env python3
"""
Performance Monitor - Monitoring prestazioni applicazione
"""

import time
import psutil
from functools import wraps
from collections import defaultdict, deque
from typing import Dict, List, Any
from datetime import datetime
from logger_config import get_logger

class PerformanceMonitor:
    """Monitor performance applicazione"""
    
    def __init__(self, max_samples: int = 1000):
        self.logger = get_logger(__name__)
        self.max_samples = max_samples
        self.metrics = defaultdict(lambda: deque(maxlen=max_samples))
        self.counters = defaultdict(int)
        
    def track_execution_time(self, operation: str):
        """Decorator per tracciare tempo esecuzione"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    execution_time = time.time() - start_time
                    self._record_metric(operation, execution_time, success)
            return wrapper
        return decorator
    
    def _record_metric(self, operation: str, execution_time: float, success: bool):
        """Registra metrica"""
        self.metrics[f"{operation}_time"].append(execution_time)
        self.counters[f"{operation}_total"] += 1
        
        if success:
            self.counters[f"{operation}_success"] += 1
        else:
            self.counters[f"{operation}_error"] += 1
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Ottieni metriche sistema"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            return {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': round((disk.used / disk.total) * 100, 1),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Errore raccolta metriche sistema: {e}")
            return {'error': str(e)}
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Ottieni metriche applicazione"""
        metrics_summary = {}
        
        for operation, times in self.metrics.items():
            if times and operation.endswith('_time'):
                operation_name = operation.replace('_time', '')
                times_list = list(times)
                
                total_calls = self.counters.get(f"{operation_name}_total", 0)
                success_calls = self.counters.get(f"{operation_name}_success", 0)
                
                metrics_summary[operation_name] = {
                    'avg_time': round(sum(times_list) / len(times_list), 3),
                    'min_time': round(min(times_list), 3),
                    'max_time': round(max(times_list), 3),
                    'total_calls': total_calls,
                    'success_calls': success_calls,
                    'error_calls': self.counters.get(f"{operation_name}_error", 0),
                    'success_rate': round((success_calls / max(total_calls, 1)) * 100, 1)
                }
        
        return {
            'operations': metrics_summary,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Ottieni stato salute sistema"""
        system_metrics = self.get_system_metrics()
        app_metrics = self.get_application_metrics()
        
        # Determina stato salute
        health_issues = []
        
        if system_metrics.get('cpu_percent', 0) > 80:
            health_issues.append("CPU usage alto")
        if system_metrics.get('memory_percent', 0) > 85:
            health_issues.append("Memoria scarsa")
        if system_metrics.get('disk_percent', 0) > 90:
            health_issues.append("Spazio disco scarso")
        
        # Controlla success rate operazioni critiche
        operations = app_metrics.get('operations', {})
        for op_name, metrics in operations.items():
            if metrics['success_rate'] < 90 and metrics['total_calls'] > 10:
                health_issues.append(f"Success rate basso per {op_name}: {metrics['success_rate']:.1f}%")
        
        status = 'healthy'
        if health_issues:
            status = 'degraded' if len(health_issues) <= 2 else 'unhealthy'
        
        return {
            'status': status,
            'issues': health_issues,
            'system_metrics': system_metrics,
            'application_metrics': app_metrics,
            'timestamp': datetime.now().isoformat()
        }

# Singleton globale
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Ottieni istanza singleton del monitor"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
