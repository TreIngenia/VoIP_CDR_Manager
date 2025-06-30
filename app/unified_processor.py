#!/usr/bin/env python3
"""
Unified Processor - Combina FTPDownloader con funzionalità di conversione
Mantiene la compatibilità con l'interfaccia originale di FTPProcessor
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from ftp_downloader import FTPDownloader
from file_converter import convert_multiple_files, is_cdr_file
from utils import extract_data_from_api

logger = logging.getLogger(__name__)

class UnifiedProcessor:
    """
    Classe che unifica FTP download e conversione file
    Compatibile con l'interfaccia originale di FTPProcessor
    """
    
    def __init__(self, config):
        """
        Inizializza il processor con configurazione
        
        Args:
            config (dict): Configurazione completa
        """
        self.config = config
        self.ensure_output_directory()
        
        # Inizializza FTPDownloader quando necessario (lazy loading)
        self._ftp_downloader = None
        
        logger.info("🔧 Unified Processor inizializzato")
    
    def ensure_output_directory(self):
        """Crea la directory di output se non esiste"""
        output_dir = Path(self.config['output_directory'])
        output_dir.mkdir(exist_ok=True)
    
    def _get_ftp_downloader(self):
        """Crea FTPDownloader solo quando serve (lazy loading)"""
        if self._ftp_downloader is None:
            self._ftp_downloader = FTPDownloader(
                host=self.config.get('ftp_host'),
                username=self.config.get('ftp_user'), 
                password=self.config.get('ftp_password'),
                port=self.config.get('ftp_port', 21)
            )
        return self._ftp_downloader
    
    def download_files(self):
        """
        Scarica i file dal server FTP basandosi sulla configurazione
        Mantiene compatibilità con FTPProcessor.download_files()
        
        Returns:
            list: Lista dei file scaricati
        """
        try:
            logger.info("🔄 Inizio download files con FTPDownloader")
            
            # Determina il template/pattern da usare
            template = self._determine_download_pattern()
            
            if not template:
                logger.warning("Nessun pattern di download specificato")
                return []
            
            # Usa FTPDownloader per il download
            downloader = self._get_ftp_downloader()
            
            if not downloader.connetti():
                logger.error("Impossibile connettersi al server FTP")
                return []
            
            try:
                # Scarica i file usando il template
                file_scaricati = downloader.scarica_per_template(
                    template=template,
                    directory_ftp=self.config.get('ftp_directory', '/'),
                    cartella_locale=self.config.get('output_directory'),
                    data=None,
                    test=False  # Download effettivo
                )
                
                # Converti nomi file in path completi
                output_dir = Path(self.config.get('output_directory'))
                full_paths = [str(output_dir / filename) for filename in file_scaricati]
                
                logger.info(f"✅ Download completato: {len(full_paths)} file scaricati")
                return full_paths
                
            finally:
                downloader.disconnetti()
                
        except Exception as e:
            logger.error(f"❌ Errore nel download files: {e}")
            return []
    
    def _determine_download_pattern(self):
        """
        Determina il pattern di download dalla configurazione
        Mantiene compatibilità con logica FTPProcessor
        
        Returns:
            str: Pattern da usare per il download
        """
        # Controlla download_all_files
        download_all_raw = self.config.get('download_all_files', False)
        
        # Conversione booleana rigorosa
        if isinstance(download_all_raw, bool):
            download_all = download_all_raw
        elif isinstance(download_all_raw, str):
            download_all = download_all_raw.lower().strip() in ('true', '1', 'yes', 'on')
        else:
            download_all = False
        
        if download_all:
            logger.info("🔄 MODALITÀ: SCARICA TUTTI I FILE")
            return "*"  # Pattern per tutti i file
        
        # Controlla specific_filename
        specific_filename = self.config.get('specific_filename')
        if specific_filename and specific_filename.strip():
            logger.info(f"🎯 Usando SPECIFIC_FILENAME: {specific_filename}")
            return specific_filename.strip()
        
        # Controlla filter_pattern  
        filter_pattern = self.config.get('filter_pattern')
        if filter_pattern and filter_pattern.strip():
            logger.info(f"🎯 Usando FILTER_PATTERN: {filter_pattern}")
            return filter_pattern.strip()
        
        # Genera pattern temporale come fallback
        pattern = self._generate_temporal_pattern()
        logger.info(f"🎯 Usando pattern temporale generato: {pattern}")
        return pattern
    
    def _generate_temporal_pattern(self):
        """
        Genera pattern temporale basato sulla configurazione
        
        Returns:
            str: Pattern temporale
        """
        pattern_type = self.config.get('file_naming_pattern', 'monthly')
        custom_pattern = self.config.get('custom_pattern', '')
        
        if pattern_type == 'custom' and custom_pattern:
            return custom_pattern
        
        # Pattern predefiniti
        now = datetime.now()
        patterns = {
            'monthly': f"RIV_*_MESE_{now.month:02d}_*.CDR",
            'yearly': f"RIV_*_MESE_*_{now.year}-*.CDR", 
            'daily': f"RIV_*_MESE_{now.month:02d}_{now.year}-{now.month:02d}-{now.day:02d}-*.CDR",
            'cdr_any': "RIV_*_MESE_*_*.CDR"
        }
        
        return patterns.get(pattern_type, patterns['monthly'])
    
    def convert_files(self, file_paths):
        """
        Converte una lista di file in JSON
        
        Args:
            file_paths (list): Lista di path dei file da convertire
            
        Returns:
            dict: Risultato della conversione
        """
        logger.info(f"🔄 Inizio conversione di {len(file_paths)} file")
        
        result = convert_multiple_files(file_paths, self.config['output_directory'])
        
        logger.info(f"✅ Conversione completata: {result['total_converted']} successi, {result['total_errors']} errori")
        
        return result
    
    def process_files(self):
        """
        Processo completo: download + conversione + elaborazione CDR
        Mantiene compatibilità con FTPProcessor.process_files()
        
        Returns:
            dict: Risultato completo del processo
        """
        try:
            logger.info("🚀 Inizio processo completo: download + conversione")
            
            # STEP 1: Download dei file
            downloaded_files = self.download_files()
            
            if not downloaded_files:
                logger.warning("Nessun file scaricato")
                return {
                    'success': False, 
                    'message': 'Nessun file scaricato - verificare pattern o disponibilità file',
                    'timestamp': datetime.now().isoformat()
                }
            
            # STEP 2: Conversione in JSON
            conversion_result = self.convert_files(downloaded_files)
            converted_files = conversion_result['converted_files']
            conversion_errors = conversion_result['conversion_errors']
            
            # STEP 3: Risultato base
            result = {
                'success': True,
                'message': f'Processo completato: {len(converted_files)} file convertiti',
                'downloaded_files': [str(f) for f in downloaded_files],
                'converted_files': [str(f) for f in converted_files],
                'total_downloaded': len(downloaded_files),
                'total_converted': len(converted_files),
                'conversion_errors': conversion_errors,
                'timestamp': datetime.now().isoformat()
            }
            
            # STEP 4: Elaborazione CDR se disponibile
            if hasattr(self, 'cdr_analytics') and converted_files:
                try:
                    cdr_results = []
                    
                    for json_file in converted_files:
                        if is_cdr_file(json_file):
                            logger.info(f"🔍 Elaborazione CDR per: {json_file}")
                            cdr_result = self.cdr_analytics.process_cdr_file(json_file)
                            
                            # Pulisci risultato CDR
                            if isinstance(cdr_result, dict):
                                clean_cdr_result = {
                                    'success': cdr_result.get('success', False),
                                    'message': cdr_result.get('message', ''),
                                    'source_file': str(cdr_result.get('source_file', '')),
                                    'total_records': cdr_result.get('total_records', 0),
                                    'total_contracts': cdr_result.get('total_contracts', 0),
                                    'generated_files': [str(f) for f in cdr_result.get('generated_files', [])],
                                    'categories_system_enabled': cdr_result.get('categories_system_enabled', False),
                                    'processing_timestamp': cdr_result.get('processing_timestamp', datetime.now().isoformat())
                                }
                                
                                # Aggiungi statistiche categorie se disponibili
                                if 'category_stats' in cdr_result:
                                    clean_cdr_result['category_stats'] = cdr_result['category_stats']
                                
                                cdr_results.append(clean_cdr_result)
                    
                    if cdr_results:
                        result['cdr_analytics'] = {
                            'processed_files': len(cdr_results),
                            'successful_analyses': sum(1 for r in cdr_results if r.get('success')),
                            'total_reports_generated': sum(len(r.get('generated_files', [])) for r in cdr_results),
                            'categories_system_enabled': any(r.get('categories_system_enabled', False) for r in cdr_results),
                            'results': cdr_results
                        }
                        
                except Exception as e:
                    logger.error(f"Errore elaborazione CDR: {e}")
                    result['cdr_analytics'] = {
                        'error': str(e),
                        'processed_files': 0
                    }
            
            logger.info(f"🎉 Processo completo completato: {len(converted_files)} file convertiti")
            
            # STEP 5: Estrazione dati API (se disponibile)
            try:
                extract_data_from_api("/api/cdr/extract_contracts")
            except Exception as e:
                logger.warning(f"Estrazione dati API fallita: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Errore nel processo completo: {e}")
            return {
                'success': False, 
                'message': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }
    
    def list_ftp_files(self):
        """
        Lista i file sul server FTP
        Mantiene compatibilità con FTPProcessor
        
        Returns:
            list: Lista dei file sul server
        """
        try:
            downloader = self._get_ftp_downloader()
            
            if not downloader.connetti():
                return []
            
            try:
                files = downloader.lista_file_ftp(self.config.get('ftp_directory', '/'))
                return files
            finally:
                downloader.disconnetti()
                
        except Exception as e:
            logger.error(f"Errore nel listare file FTP: {e}")
            return []
    
    def test_ftp_connection(self):
        """
        Testa la connessione FTP
        
        Returns:
            dict: Risultato del test
        """
        try:
            downloader = self._get_ftp_downloader()
            
            if downloader.connetti():
                try:
                    files = downloader.lista_file_ftp(self.config.get('ftp_directory', '/'))
                    return {
                        'success': True,
                        'message': f'Connessione riuscita. Trovati {len(files)} file.',
                        'file_count': len(files)
                    }
                finally:
                    downloader.disconnetti()
            else:
                return {
                    'success': False,
                    'message': 'Impossibile connettersi al server FTP'
                }
                
        except Exception as e:
            logger.error(f"Errore test connessione FTP: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    def debug_configuration(self):
        """Debug della configurazione (compatibilità)"""
        logger.info("🔧 === DEBUG CONFIGURAZIONE UNIFIED PROCESSOR ===")
        for key, value in self.config.items():
            logger.info(f"  {key} = {repr(value)} (tipo: {type(value).__name__})")
        logger.info("🔧 === FINE DEBUG ===")
    
    # Metodo per compatibilità con integrate_enhanced_cdr_system
    def _is_cdr_file(self, json_file_path):
        """Wrapper per is_cdr_file (compatibilità)"""
        return is_cdr_file(json_file_path)