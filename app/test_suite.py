#!/usr/bin/env python3
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
