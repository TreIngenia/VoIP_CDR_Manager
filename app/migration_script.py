#!/usr/bin/env python3
"""
Script di Migrazione Automatica - FTP Scheduler App
Applica tutti i miglioramenti identificati nell'analisi del progetto
"""

import os
import sys
import shutil
import json
import re
from pathlib import Path
from datetime import datetime
import subprocess

class ProjectMigrator:
    """Migra il progetto applicando tutti i miglioramenti"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.backup_dir = None
        self.migration_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log delle operazioni"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.migration_log.append(log_entry)
        
    def create_backup(self):
        """Crea backup completo del progetto"""
        self.log("🚀 Creazione backup del progetto...", "INFO")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.project_root / f"backup_{timestamp}"
        self.backup_dir.mkdir(exist_ok=True)
        
        # File da includere nel backup
        files_to_backup = [
            'app.py', 'config.py', 'routes.py', 'ftp_processor.py',
            'scheduler.py', 'cdr_categories.py', 'cdr_integration_enhanced.py',
            'categories_routes.py', 'utils.py', 'requirements.txt',
            '.env', '.env.local', '.env.example'
        ]
        
        backed_up_count = 0
        for file_path in files_to_backup:
            source = self.project_root / file_path
            if source.exists():
                shutil.copy2(source, self.backup_dir / file_path)
                backed_up_count += 1
        
        self.log(f"✅ Backup creato: {self.backup_dir} ({backed_up_count} file)", "SUCCESS")
        return True
    
    def fix_config_duplication(self):
        """Fix duplicazione in config.py"""
        self.log("🔧 Fix duplicazione config.py...", "INFO")
        
        config_file = self.project_root / 'config.py'
        if not config_file.exists():
            self.log("❌ File config.py non trovato", "ERROR")
            return False
        
        content = config_file.read_text(encoding='utf-8')
        
        # Trova e rimuovi duplicazione output_directory
        lines = content.split('\n')
        output_dir_count = 0
        fixed_lines = []
        
        for line in lines:
            if "'output_directory':" in line and "os.getenv('OUTPUT_DIRECTORY'" in line:
                output_dir_count += 1
                if output_dir_count == 1:
                    fixed_lines.append(line)  # Mantieni la prima occorrenza
                else:
                    self.log(f"Rimossa duplicazione: {line.strip()}", "DEBUG")
                    continue
            else:
                fixed_lines.append(line)
        
        # Scrivi il file corretto
        config_file.write_text('\n'.join(fixed_lines), encoding='utf-8')
        self.log("✅ Fix config.py completato", "SUCCESS")
        return True
    
    def create_logger_config(self):
        """Crea logger_config.py standardizzato"""
        self.log("📄 Creazione logger_config.py...", "INFO")
        
        logger_content = '''#!/usr/bin/env python3
"""
Logger Configuration - Sistema di logging standardizzato
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

class ProjectLogger:
    """Logger standardizzato per tutto il progetto"""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Inizializza il sistema di logging"""
        if cls._initialized:
            return
            
        # Crea directory logs
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Configura logging root
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Rimuovi handler esistenti
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Ottieni logger standardizzato"""
        cls.initialize()
        
        if name not in cls._loggers:
            cls._loggers[name] = cls._create_logger(name)
        return cls._loggers[name]
    
    @classmethod
    def _create_logger(cls, name: str) -> logging.Logger:
        """Crea nuovo logger"""
        logger = logging.getLogger(name)
        
        if logger.handlers:
            return logger
            
        logger.setLevel(logging.INFO)
        
        # Formatter comune
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
        # File handler con rotazione
        log_file = Path('logs') / 'app.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        
        return logger

def get_logger(name: str = None) -> logging.Logger:
    """Ottieni logger per modulo corrente"""
    if name is None:
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    return ProjectLogger.get_logger(name)

def log_success(message: str, logger_name: str = None):
    """Log messaggio successo"""
    logger = get_logger(logger_name)
    logger.info(f"✅ {message}")

def log_error(message: str, logger_name: str = None):
    """Log messaggio errore"""
    logger = get_logger(logger_name)
    logger.error(f"❌ {message}")

def log_warning(message: str, logger_name: str = None):
    """Log messaggio warning"""
    logger = get_logger(logger_name)
    logger.warning(f"⚠️ {message}")

def log_info(message: str, logger_name: str = None):
    """Log messaggio info"""
    logger = get_logger(logger_name)
    logger.info(f"ℹ️ {message}")
'''
        
        logger_file = self.project_root / 'logger_config.py'
        logger_file.write_text(logger_content, encoding='utf-8')
        self.log("✅ logger_config.py creato", "SUCCESS")
        return True
    
    def create_config_validator(self):
        """Crea config_validator.py"""
        self.log("📄 Creazione config_validator.py...", "INFO")
        
        validator_content = '''#!/usr/bin/env python3
"""
Config Validator - Validazione robusta della configurazione
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from logger_config import get_logger

@dataclass
class ValidationError:
    """Errore di validazione"""
    field: str
    message: str
    severity: str  # 'error', 'warning', 'info'

class ConfigValidator:
    """Validatore configurazione avanzato"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.errors: List[ValidationError] = []
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """Valida configurazione completa"""
        self.errors.clear()
        
        self._validate_ftp_config(config)
        self._validate_paths(config)
        self._validate_scheduling(config)
        self._validate_voip_prices(config)
        self._validate_patterns(config)
        
        has_errors = any(err.severity == 'error' for err in self.errors)
        return not has_errors, self.errors
    
    def _validate_ftp_config(self, config: Dict[str, Any]):
        """Valida configurazione FTP"""
        required_ftp = ['ftp_host', 'ftp_user', 'ftp_password']
        
        for field in required_ftp:
            if not config.get(field):
                self.errors.append(ValidationError(
                    field=field,
                    message=f"Campo FTP obbligatorio: {field}",
                    severity='error'
                ))
        
        # Valida formato host
        host = config.get('ftp_host', '')
        if host and not re.match(r'^[a-zA-Z0-9.-]+$', host):
            self.errors.append(ValidationError(
                field='ftp_host',
                message="Formato host FTP non valido",
                severity='error'
            ))
    
    def _validate_paths(self, config: Dict[str, Any]):
        """Valida percorsi file e directory"""
        output_dir = config.get('output_directory', '')
        
        if output_dir:
            try:
                path = Path(output_dir)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                    
                # Test scrittura
                test_file = path / '.write_test'
                test_file.touch()
                test_file.unlink()
                
            except Exception as e:
                self.errors.append(ValidationError(
                    field='output_directory',
                    message=f"Directory output non scrivibile: {e}",
                    severity='error'
                ))
    
    def _validate_scheduling(self, config: Dict[str, Any]):
        """Valida configurazione schedulazione"""
        schedule_type = config.get('schedule_type', 'monthly')
        
        valid_types = ['monthly', 'weekly', 'daily', 'interval', 'interval_precise', 'cron']
        if schedule_type not in valid_types:
            self.errors.append(ValidationError(
                field='schedule_type',
                message=f"Tipo schedulazione non valido: {schedule_type}",
                severity='error'
            ))
        
        # Valida cron expression se necessario
        if schedule_type == 'cron':
            cron_expr = config.get('cron_expression', '')
            if not self._validate_cron_expression(cron_expr):
                self.errors.append(ValidationError(
                    field='cron_expression',
                    message="Espressione cron non valida",
                    severity='error'
                ))
    
    def _validate_voip_prices(self, config: Dict[str, Any]):
        """Valida prezzi VoIP"""
        price_fields = ['voip_price_fixed', 'voip_price_mobile', 'voip_markup_percent']
        
        for field in price_fields:
            value = config.get(field, 0)
            try:
                price = float(value)
                if price < 0:
                    self.errors.append(ValidationError(
                        field=field,
                        message=f"Prezzo non può essere negativo: {field}",
                        severity='error'
                    ))
                elif price > 100 and 'markup' not in field:
                    self.errors.append(ValidationError(
                        field=field,
                        message=f"Prezzo molto alto: {price}",
                        severity='warning'
                    ))
            except (ValueError, TypeError):
                self.errors.append(ValidationError(
                    field=field,
                    message=f"Valore prezzo non numerico: {field}",
                    severity='error'
                ))
    
    def _validate_patterns(self, config: Dict[str, Any]):
        """Valida pattern di file"""
        patterns = ['specific_filename', 'custom_pattern', 'filter_pattern']
        
        for field in patterns:
            pattern = config.get(field, '')
            if pattern and not self._validate_file_pattern(pattern):
                self.errors.append(ValidationError(
                    field=field,
                    message=f"Pattern file non sicuro: {pattern}",
                    severity='warning'
                ))
    
    def _validate_cron_expression(self, cron_expr: str) -> bool:
        """Valida espressione cron"""
        if not cron_expr:
            return False
            
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
            
        # Validazione semplice
        pattern = r'^(\\*|\\d+(-\\d+)?|\\d+(,\\d+)*)$'
        return all(re.match(pattern, part) for part in parts)
    
    def _validate_file_pattern(self, pattern: str) -> bool:
        """Valida pattern file per sicurezza"""
        if not pattern:
            return True
            
        # Blocca path traversal
        if '..' in pattern:
            return False
        
        # Caratteri pericolosi
        dangerous_chars = ['|', ';', '&', '$', '`', '<', '>']
        return not any(char in pattern for char in dangerous_chars)
    
    def get_validation_summary(self) -> str:
        """Ottieni riassunto validazione"""
        if not self.errors:
            return "✅ Configurazione valida"
        
        error_count = len([e for e in self.errors if e.severity == 'error'])
        warning_count = len([e for e in self.errors if e.severity == 'warning'])
        
        summary = []
        if error_count > 0:
            summary.append(f"❌ {error_count} errori")
        if warning_count > 0:
            summary.append(f"⚠️ {warning_count} warning")
        
        return " | ".join(summary)
'''
        
        validator_file = self.project_root / 'config_validator.py'
        validator_file.write_text(validator_content, encoding='utf-8')
        self.log("✅ config_validator.py creato", "SUCCESS")
        return True
    
    def create_exception_handler(self):
        """Crea exception_handler.py"""
        self.log("📄 Creazione exception_handler.py...", "INFO")
        
        exception_content = '''#!/usr/bin/env python3
"""
Exception Handler - Gestione centralizzata delle eccezioni
"""

import traceback
from typing import Optional, Dict, Any
from functools import wraps
from datetime import datetime
from logger_config import get_logger

class ProjectException(Exception):
    """Eccezione base del progetto"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

class FTPException(ProjectException):
    """Eccezioni FTP specifiche"""
    pass

class CDRException(ProjectException):
    """Eccezioni CDR specifiche"""
    pass

class ConfigException(ProjectException):
    """Eccezioni configurazione"""
    pass

class OdooException(ProjectException):
    """Eccezioni Odoo"""
    pass

class ExceptionHandler:
    """Gestore centralizzato delle eccezioni"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def handle_exception(self, exc: Exception, context: str = None) -> Dict[str, Any]:
        """Gestisce eccezione e restituisce response standardizzata"""
        
        # Log dettagliato dell'errore
        self.logger.error(f"Eccezione in {context or 'unknown'}: {exc}")
        self.logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Determina tipo di errore e response
        if isinstance(exc, ProjectException):
            return {
                'success': False,
                'error_code': exc.error_code,
                'message': exc.message,
                'details': exc.details,
                'timestamp': exc.timestamp
            }
        elif isinstance(exc, (ConnectionError, TimeoutError)):
            return {
                'success': False,
                'error_code': 'CONNECTION_ERROR',
                'message': 'Errore di connessione',
                'details': {'original_error': str(exc)},
                'timestamp': datetime.now().isoformat()
            }
        elif isinstance(exc, (ValueError, TypeError)):
            return {
                'success': False,
                'error_code': 'VALIDATION_ERROR', 
                'message': 'Errore validazione dati',
                'details': {'original_error': str(exc)},
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Errore generico - non esporre dettagli interni
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': 'Errore interno del sistema',
                'details': {},
                'timestamp': datetime.now().isoformat()
            }

def handle_exceptions(context: str = None):
    """Decorator per gestione automatica eccezioni"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = ExceptionHandler()
                return handler.handle_exception(e, context or func.__name__)
        return wrapper
    return decorator

# Response helper per Flask
class APIResponse:
    """Standardizza response API"""
    
    @staticmethod
    def success(data: Any = None, message: str = None) -> Dict[str, Any]:
        """Response di successo"""
        response = {'success': True}
        if message:
            response['message'] = message
        if data is not None:
            response['data'] = data
        response['timestamp'] = datetime.now().isoformat()
        return response
    
    @staticmethod
    def error(message: str, error_code: str = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Response di errore"""
        return {
            'success': False,
            'message': message,
            'error_code': error_code or 'UNKNOWN_ERROR',
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
'''
        
        exception_file = self.project_root / 'exception_handler.py'
        exception_file.write_text(exception_content, encoding='utf-8')
        self.log("✅ exception_handler.py creato", "SUCCESS")
        return True
    
    def create_performance_monitor(self):
        """Crea performance_monitor.py"""
        self.log("📄 Creazione performance_monitor.py...", "INFO")
        
        monitor_content = '''#!/usr/bin/env python3
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
'''
        
        monitor_file = self.project_root / 'performance_monitor.py'
        monitor_file.write_text(monitor_content, encoding='utf-8')
        self.log("✅ performance_monitor.py creato", "SUCCESS")
        return True
    
    def create_test_suite(self):
        """Crea test suite base"""
        self.log("📄 Creazione test_suite.py...", "INFO")
        
        test_content = '''#!/usr/bin/env python3
"""
Test Suite - Test base per validare funzionalità critiche
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

class TestConfigValidator(unittest.TestCase):
    """Test per validatore configurazione"""
    
    def setUp(self):
        try:
            from config_validator import ConfigValidator
            self.validator = ConfigValidator()
        except ImportError:
            self.skipTest("config_validator non disponibile")
    
    def test_valid_config(self):
        """Test configurazione valida"""
        config = {
            'ftp_host': 'test.example.com',
            'ftp_user': 'testuser',
            'ftp_password': 'testpass',
            'output_directory': tempfile.mkdtemp(),
            'voip_price_fixed': 0.02,
            'voip_price_mobile': 0.15,
            'schedule_type': 'monthly'
        }
        
        is_valid, errors = self.validator.validate_config(config)
        self.assertTrue(is_valid)
        
        error_count = len([e for e in errors if e.severity == 'error'])
        self.assertEqual(error_count, 0)
    
    def test_invalid_ftp_config(self):
        """Test configurazione FTP non valida"""
        config = {
            'ftp_host': '',  # Host mancante
            'ftp_user': 'testuser',
            'ftp_password': 'testpass'
        }
        
        is_valid, errors = self.validator.validate_config(config)
        self.assertFalse(is_valid)
        self.assertTrue(any(e.field == 'ftp_host' for e in errors))

class TestPerformanceMonitor(unittest.TestCase):
    """Test per performance monitor"""
    
    def setUp(self):
        try:
            from performance_monitor import PerformanceMonitor
            self.monitor = PerformanceMonitor()
        except ImportError:
            self.skipTest("performance_monitor non disponibile")
    
    def test_track_execution_time(self):
        """Test tracking tempo esecuzione"""
        @self.monitor.track_execution_time('test_op')
        def test_function():
            import time
            time.sleep(0.1)
            return "success"
        
        result = test_function()
        self.assertEqual(result, "success")
        
        # Verifica che la metrica sia stata registrata
        metrics = self.monitor.get_application_metrics()
        operations = metrics.get('operations', {})
        self.assertIn('test_op', operations)
        
        test_op_metrics = operations['test_op']
        self.assertEqual(test_op_metrics['total_calls'], 1)
        self.assertEqual(test_op_metrics['success_calls'], 1)
        self.assertGreater(test_op_metrics['avg_time'], 0.05)  # Almeno 50ms
    
    def test_system_metrics(self):
        """Test raccolta metriche sistema"""
        metrics = self.monitor.get_system_metrics()
        
        # Verifica presenza campi obbligatori
        required_fields = ['cpu_percent', 'memory_percent', 'disk_percent']
        for field in required_fields:
            self.assertIn(field, metrics)
            self.assertIsInstance(metrics[field], (int, float))

class TestExceptionHandler(unittest.TestCase):
    """Test per gestore eccezioni"""
    
    def setUp(self):
        try:
            from exception_handler import ExceptionHandler, ProjectException
            self.handler = ExceptionHandler()
            self.ProjectException = ProjectException
        except ImportError:
            self.skipTest("exception_handler non disponibile")
    
    def test_handle_project_exception(self):
        """Test gestione ProjectException"""
        exc = self.ProjectException("Test error", "TEST_ERROR", {"detail": "test"})
        
        result = self.handler.handle_exception(exc, "test_context")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'TEST_ERROR')
        self.assertEqual(result['message'], 'Test error')
        self.assertEqual(result['details']['detail'], 'test')
    
    def test_handle_generic_exception(self):
        """Test gestione eccezione generica"""
        exc = ValueError("Generic error")
        
        result = self.handler.handle_exception(exc, "test_context")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'VALIDATION_ERROR')
        self.assertIn('Errore validazione', result['message'])

class TestLoggerConfig(unittest.TestCase):
    """Test per configurazione logger"""
    
    def test_get_logger(self):
        """Test creazione logger"""
        try:
            from logger_config import get_logger
            logger = get_logger('test_module')
            
            self.assertIsNotNone(logger)
            self.assertEqual(logger.name, 'test_module')
            
            # Test che il logger sia configurato correttamente
            self.assertTrue(len(logger.handlers) > 0)
            
        except ImportError:
            self.skipTest("logger_config non disponibile")

def run_integration_tests():
    """Esegue test di integrazione base"""
    print("🧪 Esecuzione test di integrazione...")
    
    try:
        # Test import moduli
        modules_to_test = [
            'logger_config',
            'config_validator', 
            'exception_handler',
            'performance_monitor'
        ]
        
        for module in modules_to_test:
            try:
                __import__(module)
                print(f"✅ {module}: Import OK")
            except ImportError as e:
                print(f"❌ {module}: Import fallito - {e}")
        
        # Test configurazione base
        try:
            from config import SecureConfig
            from config_validator import ConfigValidator
            
            config = SecureConfig()
            validator = ConfigValidator()
            
            is_valid, errors = validator.validate_config(config.get_config())
            error_count = len([e for e in errors if e.severity == 'error'])
            
            if error_count == 0:
                print("✅ Configurazione: Validazione OK")
            else:
                print(f"⚠️ Configurazione: {error_count} errori trovati")
                
        except Exception as e:
            print(f"❌ Test configurazione fallito: {e}")
        
        print("🧪 Test di integrazione completati")
        
    except Exception as e:
        print(f"❌ Errore nei test di integrazione: {e}")

if __name__ == '__main__':
    # Esegui test unittest
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Esegui test integrazione
    run_integration_tests()
'''
        
        test_file = self.project_root / 'test_suite.py'
        test_file.write_text(test_content, encoding='utf-8')
        self.log("✅ test_suite.py creato", "SUCCESS")
        return True
    
    def integrate_odoo_client(self):
        """Integra gen_odoo_invoice_token.py nel sistema principale"""
        self.log("🔧 Integrazione client Odoo...", "INFO")
        
        odoo_file = self.project_root / 'gen_odoo_invoice_token.py'
        if not odoo_file.exists():
            self.log("⚠️ File gen_odoo_invoice_token.py non trovato, skip", "WARNING")
            return True
        
        # Crea odoo_integration.py migliorato
        odoo_content = '''#!/usr/bin/env python3
"""
Odoo Integration - Client Odoo integrato nel sistema principale
Sostituisce gen_odoo_invoice_token.py con architettura migliorata
"""

import xmlrpc.client
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from logger_config import get_logger
from exception_handler import OdooException

@dataclass
class InvoiceItem:
    """Item fattura"""
    product_id: int
    quantity: float
    price_unit: float
    name: str
    description: str = ""

@dataclass  
class InvoiceData:
    """Dati fattura completi"""
    partner_id: int
    items: List[InvoiceItem]
    due_days: Optional[int] = None
    manual_due_date: Optional[str] = None
    reference: str = ""

class OdooClient:
    """Client Odoo integrato e migliorato"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(__name__)
        self.uid = None
        self.models = None
        self.common = None
        self._validate_config()
    
    def _validate_config(self):
        """Valida configurazione Odoo"""
        required_keys = ['ODOO_URL', 'ODOO_DB', 'ODOO_USERNAME', 'ODOO_API_KEY']
        missing = [k for k in required_keys if not self.config.get(k)]
        
        if missing:
            raise OdooException(f"Configurazione Odoo incompleta: {missing}", 'CONFIG_ERROR')
    
    def connect(self) -> bool:
        """Connessione e autenticazione Odoo"""
        try:
            self.common = xmlrpc.client.ServerProxy(f"{self.config['ODOO_URL']}/xmlrpc/2/common")
            
            self.uid = self.common.authenticate(
                self.config['ODOO_DB'],
                self.config['ODOO_USERNAME'], 
                self.config['ODOO_API_KEY'],
                {}
            )
            
            if not self.uid:
                raise OdooException("Autenticazione Odoo fallita", 'AUTH_ERROR')
            
            self.models = xmlrpc.client.ServerProxy(f"{self.config['ODOO_URL']}/xmlrpc/2/object")
            self.logger.info(f"Connesso ad Odoo con UID: {self.uid}")
            return True
            
        except Exception as e:
            error_msg = f"Errore connessione Odoo: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'CONNECTION_ERROR')
    
    def execute(self, model: str, method: str, *args, **kwargs):
        """Wrapper per execute_kw con gestione errori"""
        if not self.uid or not self.models:
            if not self.connect():
                raise OdooException("Impossibile connettersi ad Odoo", 'CONNECTION_ERROR')
        
        try:
            if kwargs:
                return self.models.execute_kw(
                    self.config['ODOO_DB'], self.uid, self.config['ODOO_API_KEY'],
                    model, method, list(args), kwargs
                )
            else:
                return self.models.execute_kw(
                    self.config['ODOO_DB'], self.uid, self.config['ODOO_API_KEY'],
                    model, method, list(args)
                )
        except Exception as e:
            error_msg = f"Errore esecuzione {model}.{method}: {e}"
            self.logger.error(error_msg)
            raise OdooException(error_msg, 'EXECUTION_ERROR')
    
    def create_invoice(self, invoice_data: InvoiceData) -> Optional[int]:
        """Crea fattura singola"""
        try:
            # Prepara dati fattura
            invoice_vals = self._prepare_invoice_data(invoice_data)
            
            # Crea fattura
            invoice_id = self.execute('account.move', 'create', [invoice_vals])
            
            self.logger.info(f"Fattura creata con ID: {invoice_id}")
            return invoice_id
            
        except Exception as e:
            self.logger.error(f"Errore creazione fattura: {e}")
            raise OdooException(f"Errore creazione fattura: {e}", 'INVOICE_CREATE_ERROR')
    
    def create_and_confirm_invoice(self, invoice_data: InvoiceData) -> Optional[int]:
        """Crea e conferma fattura in un unico passaggio"""
        try:
            # Crea fattura
            invoice_id = self.create_invoice(invoice_data)
            
            if not invoice_id:
                return None
            
            # Conferma fattura
            if self.confirm_invoice(invoice_id):
                self.logger.info(f"Fattura {invoice_id} creata e confermata")
                return invoice_id
            else:
                self.logger.warning(f"Fattura {invoice_id} creata ma non confermata")
                return invoice_id
                
        except Exception as e:
            self.logger.error(f"Errore creazione e conferma fattura: {e}")
            raise
    
    def confirm_invoice(self, invoice_id: int) -> bool:
        """Conferma una fattura"""
        try:
            # Verifica stato fattura
            invoice_data = self.execute('account.move', 'read', invoice_id, 
                                      fields=['state', 'name'])
            
            invoice = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
            current_state = invoice.get('state', 'draft')
            
            if current_state == 'posted':
                self.logger.info('Fattura già confermata')
                return True
            elif current_state == 'draft':
                # Conferma fattura
                self.execute('account.move', 'action_post', invoice_id)
                self.logger.info('Fattura confermata')
                return True
            else:
                self.logger.warning(f'Stato fattura non gestito: {current_state}')
                return False
                
        except Exception as e:
            self.logger.error(f'Errore conferma fattura: {e}')
            raise OdooException(f'Errore conferma fattura: {e}', 'INVOICE_CONFIRM_ERROR')
    
    def _prepare_invoice_data(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """Prepara dati per creazione fattura"""
        # Calcola data scadenza
        invoice_date = datetime.now().strftime('%Y-%m-%d')
        due_date = self._calculate_due_date(invoice_date, invoice_data)
        
        # Prepara righe fattura
        invoice_lines = []
        for item in invoice_data.items:
            line_vals = {
                'product_id': item.product_id,
                'quantity': item.quantity,
                'price_unit': item.price_unit,
                'name': item.name,
            }
            if item.description:
                line_vals['description'] = item.description
                
            invoice_lines.append((0, 0, line_vals))
        
        invoice_vals = {
            'partner_id': invoice_data.partner_id,
            'move_type': 'out_invoice',
            'invoice_date': invoice_date,
            'invoice_date_due': due_date,
            'invoice_line_ids': invoice_lines,
        }
        
        if invoice_data.reference:
            invoice_vals['ref'] = invoice_data.reference
        
        return invoice_vals
    
    def _calculate_due_date(self, invoice_date: str, invoice_data: InvoiceData) -> str:
        """Calcola data scadenza fattura"""
        invoice_dt = datetime.strptime(invoice_date, '%Y-%m-%d')
        
        if invoice_data.manual_due_date:
            return invoice_data.manual_due_date
        elif invoice_data.due_days:
            due_dt = invoice_dt + timedelta(days=invoice_data.due_days)
            return due_dt.strftime('%Y-%m-%d')
        else:
            # Default 30 giorni
            due_dt = invoice_dt + timedelta(days=30)
            return due_dt.strftime('%Y-%m-%d')
    
    def get_invoice_details(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Ottieni dettagli di una fattura"""
        try:
            invoice_data = self.execute('account.move', 'read', invoice_id,
                                      fields=['name', 'partner_id', 'invoice_date', 
                                             'invoice_date_due', 'amount_total', 'state'])
            
            if invoice_data:
                inv = invoice_data[0] if isinstance(invoice_data, list) else invoice_data
                return {
                    'name': inv.get('name'),
                    'partner_name': inv['partner_id'][1] if inv.get('partner_id') else None,
                    'invoice_date': inv.get('invoice_date'),
                    'due_date': inv.get('invoice_date_due'),
                    'amount_total': inv.get('amount_total'),
                    'state': inv.get('state')
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero dettagli fattura: {e}")
            raise OdooException(f"Errore recupero dettagli fattura: {e}", 'INVOICE_READ_ERROR')

def create_odoo_client(config: Dict[str, Any]) -> OdooClient:
    """Factory function per creare client Odoo"""
    return OdooClient(config)

# Esempi di utilizzo
def example_create_invoice():
    """Esempio creazione fattura"""
    # Configurazione (normalmente da SecureConfig)
    config = {
        'ODOO_URL': 'https://mysite.odoo.com/',
        'ODOO_DB': 'mydb',
        'ODOO_USERNAME': 'user@domain.com',
        'ODOO_API_KEY': 'api_key_here'
    }
    
    # Crea client
    client = create_odoo_client(config)
    
    # Dati fattura
    items = [
        InvoiceItem(
            product_id=41,
            quantity=2,
            price_unit=100.0,
            name='Prodotto 1',
            description='Descrizione prodotto 1'
        ),
        InvoiceItem(
            product_id=41,
            quantity=1,
            price_unit=200.0,
            name='Prodotto 2'
        )
    ]
    
    invoice_data = InvoiceData(
        partner_id=8378,
        items=items,
        due_days=30,
        reference='Fattura da sistema automatico'
    )
    
    # Crea e conferma fattura
    try:
        invoice_id = client.create_and_confirm_invoice(invoice_data)
        if invoice_id:
            print(f"✅ Fattura creata: {invoice_id}")
            
            # Ottieni dettagli
            details = client.get_invoice_details(invoice_id)
            if details:
                print(f"📄 Fattura: {details['name']}")
                print(f"💰 Totale: €{details['amount_total']}")
        else:
            print("❌ Errore creazione fattura")
            
    except OdooException as e:
        print(f"❌ Errore Odoo: {e}")
    except Exception as e:
        print(f"❌ Errore generico: {e}")

if __name__ == '__main__':
    example_create_invoice()
'''
        
        odoo_integration_file = self.project_root / 'odoo_integration.py'
        odoo_integration_file.write_text(odoo_content, encoding='utf-8')
        
        # Rinomina il vecchio file
        old_odoo_backup = self.project_root / f'gen_odoo_invoice_token_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
        odoo_file.rename(old_odoo_backup)
        
        self.log("✅ Client Odoo integrato", "SUCCESS")
        self.log(f"📦 Vecchio file archiviato: {old_odoo_backup.name}", "INFO")
        return True
    
    def update_requirements(self):
        """Aggiorna requirements.txt con dipendenze migliorate"""
        self.log("📋 Aggiornamento requirements.txt...", "INFO")
        
        new_requirements = '''# requirements.txt - Dipendenze aggiornate e sicure

# Framework web
Flask>=3.0.0,<4.0.0
Werkzeug>=3.0.0,<4.0.0
Jinja2>=3.1.2,<4.0.0
MarkupSafe>=2.1.3,<3.0.0
itsdangerous>=2.1.2,<3.0.0
click>=8.1.7,<9.0.0
blinker>=1.7.0,<2.0.0

# Schedulazione
APScheduler>=3.10.4,<4.0.0
pytz>=2024.1
tzlocal>=5.2,<6.0.0

# Elaborazione dati
pandas>=2.2.0,<3.0.0
openpyxl>=3.1.2,<4.0.0
xlrd>=2.0.1,<3.0.0

# Networking e HTTP
requests>=2.31.0,<3.0.0

# Utilità date e configurazione
python-dateutil>=2.8.2,<3.0.0
python-dotenv>=1.0.0,<2.0.0
six>=1.16.0,<2.0.0

# Logging strutturato
structlog>=24.1.0,<25.0.0

# Sicurezza aggiuntiva
cryptography>=42.0.0,<43.0.0

# Per info sistema e monitoring
psutil>=5.9.0,<6.0.0

# Development e testing (opzionale)
# pytest>=8.0.0,<9.0.0
# pytest-cov>=4.0.0,<5.0.0
# black>=24.0.0,<25.0.0
# flake8>=7.0.0,<8.0.0
# mypy>=1.8.0,<2.0.0

# Server FTP per testing (opzionale)
# pyftpdlib>=1.5.7,<2.0.0
'''
        
        requirements_file = self.project_root / 'requirements.txt'
        
        # Backup del vecchio requirements
        if requirements_file.exists():
            backup_req = self.project_root / f'requirements_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            shutil.copy2(requirements_file, backup_req)
            self.log(f"📦 Backup requirements: {backup_req.name}", "INFO")
        
        requirements_file.write_text(new_requirements, encoding='utf-8')
        self.log("✅ requirements.txt aggiornato", "SUCCESS")
        return True
    
    def update_main_files(self):
        """Aggiorna file principali con import dei nuovi moduli"""
        self.log("🔧 Aggiornamento file principali...", "INFO")
        
        # Aggiorna app.py
        self._update_app_py()
        
        # Aggiorna config.py
        self._update_config_py()
        
        # Aggiorna routes.py  
        self._update_routes_py()
        
        return True
    
    def _update_app_py(self):
        """Aggiorna app.py con nuovi import"""
        app_file = self.project_root / 'app.py'
        if not app_file.exists():
            self.log("⚠️ File app.py non trovato", "WARNING")
            return
        
        content = app_file.read_text(encoding='utf-8')
        
        # Aggiungi import dei nuovi moduli dopo gli import esistenti
        new_imports = '''
# Import moduli migliorati (aggiunti da migrazione)
from logger_config import get_logger, log_success, log_error, log_warning, log_info
from config_validator import ConfigValidator
from performance_monitor import get_performance_monitor
from exception_handler import ExceptionHandler'''
        
        # Trova la posizione dove inserire gli import
        if 'from config import SecureConfig' in content:
            content = content.replace(
                'from config import SecureConfig',
                f'from config import SecureConfig{new_imports}'
            )
        else:
            # Aggiungi all'inizio degli import locali
            content = new_imports + '\n\n' + content
        
        # Aggiungi route performance alla fine della funzione main
        performance_routes = '''
    # Route performance monitoring (aggiunto da migrazione)
    @app.route('/api/metrics/performance')
    def get_performance_metrics():
        monitor = get_performance_monitor()
        return jsonify(monitor.get_application_metrics())
    
    @app.route('/api/health/detailed')
    def get_detailed_health():
        monitor = get_performance_monitor()
        return jsonify(monitor.get_health_status())'''
        
        # Cerca dove aggiungere le route (prima del return dell'app)
        if 'return app' in content:
            content = content.replace(
                'return app',
                f'{performance_routes}\n    \n    return app'
            )
        
        app_file.write_text(content, encoding='utf-8')
        self.log("✅ app.py aggiornato", "SUCCESS")
    
    def _update_config_py(self):
        """Aggiorna config.py sostituendo logging duplicato"""
        config_file = self.project_root / 'config.py'
        if not config_file.exists():
            self.log("⚠️ File config.py non trovato", "WARNING")
            return
        
        content = config_file.read_text(encoding='utf-8')
        
        # Sostituisci import logging custom con il nuovo sistema
        if 'def setup_logging():' in content:
            # Trova e sostituisci la funzione setup_logging e le helper
            pattern = r'def setup_logging\(\):.*?def log_info\(message\):\s+.*?logger\.info\(f"\[INFO\] \{message\}"\)'
            import re
            
            replacement = '''# Usa il nuovo sistema di logging standardizzato
from logger_config import get_logger, log_success, log_error, log_warning, log_info

# Inizializza logging
logger = get_logger(__name__)'''
            
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        config_file.write_text(content, encoding='utf-8')
        self.log("✅ config.py aggiornato", "SUCCESS")
    
    def _update_routes_py(self):
        """Aggiorna routes.py con gestione errori migliorata"""
        routes_file = self.project_root / 'routes.py'
        if not routes_file.exists():
            self.log("⚠️ File routes.py non trovato", "WARNING")
            return
        
        content = routes_file.read_text(encoding='utf-8')
        
        # Aggiungi import dei nuovi moduli
        new_imports = '''from logger_config import get_logger
from exception_handler import handle_exceptions, APIResponse, ExceptionHandler
from performance_monitor import get_performance_monitor'''
        
        if 'import logging' in content:
            content = content.replace(
                'import logging',
                f'import logging\n{new_imports}'
            )
        
        # Sostituisci logger = logging.getLogger(__name__)
        content = content.replace(
            'logger = logging.getLogger(__name__)',
            'logger = get_logger(__name__)'
        )
        
        routes_file.write_text(content, encoding='utf-8')
        self.log("✅ routes.py aggiornato", "SUCCESS")
    
    def run_tests(self):
        """Esegue test suite per verificare migrazione"""
        self.log("🧪 Esecuzione test di verifica...", "INFO")
        
        try:
            # Test import moduli
            test_modules = [
                'logger_config',
                'config_validator',
                'exception_handler', 
                'performance_monitor'
            ]
            
            success_count = 0
            for module in test_modules:
                try:
                    __import__(module)
                    self.log(f"✅ {module}: Import OK", "SUCCESS")
                    success_count += 1
                except ImportError as e:
                    self.log(f"❌ {module}: Import fallito - {e}", "ERROR")
            
            # Test configurazione
            try:
                from config import SecureConfig
                config = SecureConfig()
                self.log("✅ SecureConfig: OK", "SUCCESS")
                success_count += 1
            except Exception as e:
                self.log(f"❌ SecureConfig: Errore - {e}", "ERROR")
            
            # Test validatore se disponibile
            try:
                from config_validator import ConfigValidator
                validator = ConfigValidator()
                is_valid, errors = validator.validate_config(config.get_config())
                
                error_count = len([e for e in errors if e.severity == 'error'])
                if error_count == 0:
                    self.log("✅ Validazione configurazione: OK", "SUCCESS")
                else:
                    self.log(f"⚠️ Validazione: {error_count} errori", "WARNING")
                
                success_count += 1
            except Exception as e:
                self.log(f"❌ ConfigValidator: Errore - {e}", "ERROR")
            
            # Riepilogo test
            total_tests = len(test_modules) + 2  # + SecureConfig + Validazione
            self.log(f"🧪 Test completati: {success_count}/{total_tests} riusciti", "INFO")
            
            return success_count >= (total_tests * 0.8)  # 80% successo minimo
            
        except Exception as e:
            self.log(f"❌ Errore nei test: {e}", "ERROR")
            return False
    
    def create_migration_summary(self):
        """Crea riassunto della migrazione"""
        self.log("📊 Creazione riassunto migrazione...", "INFO")
        
        summary = {
            'migration_timestamp': datetime.now().isoformat(),
            'backup_directory': str(self.backup_dir),
            'files_created': [
                'logger_config.py',
                'config_validator.py',
                'exception_handler.py', 
                'performance_monitor.py',
                'test_suite.py',
                'odoo_integration.py'
            ],
            'files_updated': [
                'app.py',
                'config.py', 
                'routes.py',
                'requirements.txt'
            ],
            'migration_log': self.migration_log
        }
        
        summary_file = self.project_root / f'migration_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
        
        self.log(f"📊 Riassunto salvato: {summary_file.name}", "SUCCESS")
        return summary_file
    
    def print_next_steps(self):
        """Stampa i prossimi passi da seguire"""
        print("\n" + "="*60)
        print("🎉 MIGRAZIONE COMPLETATA!")
        print("="*60)
        print()
        print("📋 PROSSIMI PASSI:")
        print("1. 📦 Installa nuove dipendenze:")
        print("   pip install -r requirements.txt")
        print()
        print("2. 🧪 Testa la migrazione:")
        print("   python test_suite.py")
        print()
        print("3. 🚀 Avvia l'applicazione:")
        print("   python app.py")
        print()
        print("4. 🌐 Verifica nuovi endpoint:")
        print("   http://localhost:5001/api/metrics/performance")
        print("   http://localhost:5001/api/health/detailed")
        print()
        print("5. 📊 Controlla i log:")
        print("   Visualizza: logs/app.log")
        print()
        print("📁 FILE CREATI:")
        for file in ['logger_config.py', 'config_validator.py', 'exception_handler.py', 
                    'performance_monitor.py', 'test_suite.py', 'odoo_integration.py']:
            print(f"   ✨ {file}")
        print()
        print(f"📦 BACKUP: {self.backup_dir}")
        print("="*60)
    
    def migrate(self):
        """Esegue migrazione completa"""
        try:
            self.log("🚀 AVVIO MIGRAZIONE PROGETTO FTP SCHEDULER", "INFO")
            self.log("="*50, "INFO")
            
            # 1. Backup
            if not self.create_backup():
                return False
            
            # 2. Fix immediati
            self.log("\n🔧 APPLICAZIONE FIX IMMEDIATI", "INFO")
            self.fix_config_duplication()
            
            # 3. Creazione nuovi moduli
            self.log("\n📄 CREAZIONE NUOVI MODULI", "INFO")
            self.create_logger_config()
            self.create_config_validator()
            self.create_exception_handler()
            self.create_performance_monitor()
            self.create_test_suite()
            
            # 4. Integrazione Odoo
            self.log("\n🔧 INTEGRAZIONE SISTEMA ODOO", "INFO")
            self.integrate_odoo_client()
            
            # 5. Aggiornamento dipendenze
            self.log("\n📋 AGGIORNAMENTO DIPENDENZE", "INFO")
            self.update_requirements()
            
            # 6. Aggiornamento file principali
            self.log("\n🔧 AGGIORNAMENTO FILE PRINCIPALI", "INFO")
            self.update_main_files()
            
            # 7. Test di verifica
            self.log("\n🧪 TEST DI VERIFICA", "INFO")
            test_success = self.run_tests()
            
            # 8. Riassunto
            self.log("\n📊 CREAZIONE RIASSUNTO", "INFO")
            summary_file = self.create_migration_summary()
            
            # 9. Risultato finale
            if test_success:
                self.log("\n✅ MIGRAZIONE COMPLETATA CON SUCCESSO!", "SUCCESS")
                self.print_next_steps()
                return True
            else:
                self.log("\n⚠️ MIGRAZIONE COMPLETATA CON ALCUNI PROBLEMI", "WARNING")
                self.log("Controlla i log sopra per dettagli", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"\n❌ ERRORE DURANTE MIGRAZIONE: {e}", "ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False

def main():
    """Funzione principale"""
    print("🚀 Script di Migrazione Automatica - FTP Scheduler App")
    print("=" * 60)
    print()
    print("Questo script applicherà tutti i miglioramenti identificati:")
    print("✨ Nuovi moduli: logging, validazione, monitoring, test")
    print("🔧 Fix problemi: duplicazioni, gestione errori")  
    print("🔗 Integrazione: client Odoo migliorato")
    print("📋 Aggiornamento: dipendenze e configurazioni")
    print()
    
    # Chiedi conferma
    response = input("Procedere con la migrazione? (y/N): ").strip().lower()
    if response not in ['y', 'yes', 'sì', 'si']:
        print("❌ Migrazione annullata")
        return
    
    # Verifica che siamo nella directory corretta
    if not Path('app.py').exists():
        print("❌ ERRORE: Non trovo app.py nella directory corrente")
        print("   Assicurati di eseguire lo script dalla root del progetto")
        return
    
    # Esegui migrazione
    migrator = ProjectMigrator()
    success = migrator.migrate()
    
    if success:
        print("\n🎉 Migrazione completata con successo!")
        print("Segui i prossimi passi mostrati sopra per completare l'aggiornamento")
    else:
        print("\n❌ Migrazione fallita o completata con errori")
        print("Controlla i log per maggiori dettagli")
        print(f"📦 I file originali sono salvati in: {migrator.backup_dir}")

if __name__ == "__main__":
    main()