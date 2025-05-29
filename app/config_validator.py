#!/usr/bin/env python3
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
        pattern = r'^(\*|\d+(-\d+)?|\d+(,\d+)*)$'
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
