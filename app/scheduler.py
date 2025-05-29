import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import atexit

logger = logging.getLogger(__name__)

class SchedulerManager:
    """Gestione centralizzata dello scheduler"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown())
        self.config = None
        self.job_function = None
    
    def set_config(self, config):
        """Imposta la configurazione"""
        self.config = config
    
    def set_job_function(self, job_function):
        """Imposta la funzione da eseguire"""
        self.job_function = job_function
    
    def restart_scheduler(self):
        """Riavvia lo scheduler con la nuova configurazione"""
        if not self.config or not self.job_function:
            logger.error("Configurazione o funzione job non impostata")
            return False
        
        # Rimuove tutti i job esistenti
        self.scheduler.remove_all_jobs()
        
        try:
            if self.config['schedule_type'] == 'monthly':
                self.scheduler.add_job(
                    func=self.job_function,
                    trigger=CronTrigger(
                        day=self.config['schedule_day'],
                        hour=self.config['schedule_hour'],
                        minute=self.config['schedule_minute']
                    ),
                    id='monthly_job',
                    replace_existing=True
                )
                logger.info(f"[OK] Schedulazione mensile: giorno {self.config['schedule_day']} alle {self.config['schedule_hour']}:{self.config['schedule_minute']:02d}")
                
            elif self.config['schedule_type'] == 'weekly':
                self.scheduler.add_job(
                    func=self.job_function,
                    trigger=CronTrigger(
                        day_of_week=self.config['schedule_day'],
                        hour=self.config['schedule_hour'],
                        minute=self.config['schedule_minute']
                    ),
                    id='weekly_job',
                    replace_existing=True
                )
                logger.info(f"[OK] Schedulazione settimanale: giorno {self.config['schedule_day']} alle {self.config['schedule_hour']}:{self.config['schedule_minute']:02d}")
                
            elif self.config['schedule_type'] == 'daily':
                self.scheduler.add_job(
                    func=self.job_function,
                    trigger=CronTrigger(
                        hour=self.config['schedule_hour'],
                        minute=self.config['schedule_minute']
                    ),
                    id='daily_job',
                    replace_existing=True
                )
                logger.info(f"[OK] Schedulazione giornaliera alle {self.config['schedule_hour']}:{self.config['schedule_minute']:02d}")
                
            elif self.config['schedule_type'] == 'interval':
                # Usa il vecchio sistema (giorni)
                self.scheduler.add_job(
                    func=self.job_function,
                    trigger=IntervalTrigger(days=self.config['interval_days']),
                    id='interval_job',
                    replace_existing=True
                )
                logger.info(f"[OK] Schedulazione a intervallo: ogni {self.config['interval_days']} giorni")
                
            elif self.config['schedule_type'] == 'interval_precise':
                # Nuovo sistema con minuti/ore/giorni
                interval_type = self.config.get('schedule_interval_type', 'minutes')
                interval_value = self.config.get('schedule_interval_value', 30)
                
                if interval_type == 'minutes':
                    self.scheduler.add_job(
                        func=self.job_function,
                        trigger=IntervalTrigger(minutes=interval_value),
                        id='interval_precise_job',
                        replace_existing=True
                    )
                    logger.info(f"[OK] Schedulazione precisa: ogni {interval_value} minuti")
                    
                elif interval_type == 'hours':
                    self.scheduler.add_job(
                        func=self.job_function,
                        trigger=IntervalTrigger(hours=interval_value),
                        id='interval_precise_job',
                        replace_existing=True
                    )
                    logger.info(f"[OK] Schedulazione precisa: ogni {interval_value} ore")
                    
                elif interval_type == 'seconds':
                    self.scheduler.add_job(
                        func=self.job_function,
                        trigger=IntervalTrigger(seconds=interval_value),
                        id='interval_precise_job',
                        replace_existing=True
                    )
                    logger.info(f"[OK] Schedulazione precisa: ogni {interval_value} secondi")
                    
                else:  # days
                    self.scheduler.add_job(
                        func=self.job_function,
                        trigger=IntervalTrigger(days=interval_value),
                        id='interval_precise_job',
                        replace_existing=True
                    )
                    logger.info(f"[OK] Schedulazione precisa: ogni {interval_value} giorni")
                    
            elif self.config['schedule_type'] == 'cron':
                # Parsing manuale dell'espressione cron
                parts = self.config['cron_expression'].split()
                if len(parts) == 5:
                    self.scheduler.add_job(
                        func=self.job_function,
                        trigger=CronTrigger(
                            minute=parts[0],
                            hour=parts[1],
                            day=parts[2],
                            month=parts[3],
                            day_of_week=parts[4]
                        ),
                        id='cron_job',
                        replace_existing=True
                    )
                    logger.info(f"[OK] Schedulazione cron: {self.config['cron_expression']}")
                else:
                    logger.error(f"[ERROR] Espressione cron non valida: {self.config['cron_expression']}")
                    return False
                    
            # Mostra prossima esecuzione
            jobs = self.scheduler.get_jobs()
            if jobs:
                next_run = jobs[0].next_run_time
                if next_run:
                    logger.info(f"[TIME] Prossima esecuzione: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            return True
                    
        except Exception as e:
            logger.error(f"[ERROR] Errore nella configurazione scheduler: {e}")
            return False
    
    def get_schedule_description(self):
        """Restituisce una descrizione user-friendly della schedulazione corrente"""
        if not self.config:
            return "Non configurato"
            
        try:
            schedule_type = self.config['schedule_type']
            
            if schedule_type == 'monthly':
                return f"Mensile: giorno {self.config['schedule_day']} alle {self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
                
            elif schedule_type == 'weekly':
                days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
                day_name = days[self.config['schedule_day']] if self.config['schedule_day'] < 7 else 'Sconosciuto'
                return f"Settimanale: ogni {day_name} alle {self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
                
            elif schedule_type == 'daily':
                return f"Giornaliero: ogni giorno alle {self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
                
            elif schedule_type == 'interval':
                return f"Intervallo: ogni {self.config['interval_days']} giorni"
                
            elif schedule_type == 'interval_precise':
                interval_type = self.config.get('schedule_interval_type', 'minutes')
                interval_value = self.config.get('schedule_interval_value', 30)
                
                type_labels = {
                    'seconds': 'secondi',
                    'minutes': 'minuti', 
                    'hours': 'ore',
                    'days': 'giorni'
                }
                
                return f"Intervallo preciso: ogni {interval_value} {type_labels.get(interval_type, 'unità')}"
                
            elif schedule_type == 'cron':
                return f"Cron: {self.config['cron_expression']}"
                
            return "Non configurato"
            
        except Exception as e:
            logger.error(f"Errore nella descrizione schedulazione: {e}")
            return "Errore configurazione"
    
    def get_next_scheduled_jobs(self, limit=3):
        """Restituisce le prossime esecuzioni programmate"""
        try:
            jobs = self.scheduler.get_jobs()
            next_runs = []
            
            for job in jobs:
                if job.next_run_time:
                    next_runs.append({
                        'job_id': job.id,
                        'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'next_run_iso': job.next_run_time.isoformat()
                    })
            
            # Ordina per data più vicina
            next_runs.sort(key=lambda x: x['next_run_iso'])
            
            return next_runs[:limit]
            
        except Exception as e:
            logger.error(f"Errore nel recupero prossime esecuzioni: {e}")
            return []
    
    def get_job_info(self):
        """Restituisce informazioni sui job attivi"""
        try:
            jobs = self.scheduler.get_jobs()
            job_info = []
            
            for job in jobs:
                job_info.append({
                    'id': job.id,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                    'func_name': job.func.__name__ if hasattr(job, 'func') else 'Unknown'
                })
            
            return job_info
            
        except Exception as e:
            logger.error(f"Errore nel recupero info job: {e}")
            return []
    
    def is_running(self):
        """Verifica se lo scheduler è in esecuzione"""
        return self.scheduler.running
    
    def shutdown(self):
        """Shutdown graceful dello scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Scheduler fermato correttamente")
        except Exception as e:
            logger.error(f"Errore durante shutdown scheduler: {e}")

def set_schedule_every_minute(scheduler_manager):
    """Configura esecuzione ogni minuto"""
    scheduler_manager.config['schedule_type'] = 'interval_precise'
    scheduler_manager.config['schedule_interval_type'] = 'minutes'
    scheduler_manager.config['schedule_interval_value'] = 1
    scheduler_manager.restart_scheduler()
    logger.info("[CLOCK] Schedulazione impostata: ogni minuto")

def set_schedule_every_hour(scheduler_manager):
    """Configura esecuzione ogni ora"""
    scheduler_manager.config['schedule_type'] = 'interval_precise'
    scheduler_manager.config['schedule_interval_type'] = 'hours'
    scheduler_manager.config['schedule_interval_value'] = 1
    scheduler_manager.restart_scheduler()
    logger.info("[CLOCK] Schedulazione impostata: ogni ora")

def set_schedule_every_30_minutes(scheduler_manager):
    """Configura esecuzione ogni 30 minuti"""
    scheduler_manager.config['schedule_type'] = 'interval_precise'
    scheduler_manager.config['schedule_interval_type'] = 'minutes'
    scheduler_manager.config['schedule_interval_value'] = 30
    scheduler_manager.restart_scheduler()
    logger.info("[CLOCK] Schedulazione impostata: ogni 30 minuti")

def set_schedule_every_10_seconds(scheduler_manager):
    """Configura esecuzione ogni 10 secondi (per test)"""
    scheduler_manager.config['schedule_type'] = 'interval_precise'
    scheduler_manager.config['schedule_interval_type'] = 'seconds'
    scheduler_manager.config['schedule_interval_value'] = 10
    scheduler_manager.restart_scheduler()
    logger.info("[CLOCK] Schedulazione impostata: ogni 10 secondi (TEST)")