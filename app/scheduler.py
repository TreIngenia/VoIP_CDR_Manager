import logging
import atexit
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class SchedulerManager:
    """Gestione centralizzata dello scheduler con configurazione semplificata"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        atexit.register(self._shutdown)
        
        self.config = {}
        self.job_function = None
    
    def _shutdown(self):
        """Shutdown automatico dello scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
    
    def set_config(self, secure_config):
        """Imposta la configurazione del scheduler"""
        config = secure_config.get_config()
        self.config = config
    
    def set_job_function(self, job_function):
        """Imposta la funzione da eseguire periodicamente"""
        self.job_function = job_function
    
    def restart_scheduler(self):
        """Riavvia lo scheduler con la configurazione attuale"""
        if not self._validate_setup():
            return False
        
        # Pulisce i job esistenti
        self.scheduler.remove_all_jobs()
        
        try:
            success = self._create_job()
            if success:
                self._log_next_execution()
            return success
            
        except Exception as e:
            logger.error(f"Errore configurazione scheduler: {e}")
            return False
    
    def _validate_setup(self):
        """Verifica che configurazione e funzione siano impostate"""
        if not self.config:
            logger.error("Configurazione non impostata")
            return False
        if not self.job_function:
            logger.error("Funzione job non impostata")
            return False
        return True
    
    def _create_job(self):
        """Crea il job in base al tipo di schedulazione"""
        schedule_type = self.config.get('schedule_type')
        
        job_creators = {
            'monthly': self._create_monthly_job,
            'weekly': self._create_weekly_job,
            'daily': self._create_daily_job,
            'interval': self._create_interval_job,
            'interval_precise': self._create_precise_interval_job,
            'cron': self._create_cron_job
        }
        
        creator = job_creators.get(schedule_type)
        if not creator:
            logger.error(f"Tipo schedulazione non supportato: {schedule_type}")
            return False
        
        return creator()
    
    def _create_monthly_job(self):
        """Crea schedulazione mensile"""
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
        
        day = self.config['schedule_day']
        time = f"{self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
        logger.info(f"Schedulazione mensile: giorno {day} alle {time}")
        return True
    
    def _create_weekly_job(self):
        """Crea schedulazione settimanale"""
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
        
        day = self.config['schedule_day']
        time = f"{self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
        logger.info(f"Schedulazione settimanale: giorno {day} alle {time}")
        return True
    
    def _create_daily_job(self):
        """Crea schedulazione giornaliera"""
        self.scheduler.add_job(
            func=self.job_function,
            trigger=CronTrigger(
                hour=self.config['schedule_hour'],
                minute=self.config['schedule_minute']
            ),
            id='daily_job',
            replace_existing=True
        )
        
        time = f"{self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
        logger.info(f"Schedulazione giornaliera alle {time}")
        return True
    
    def _create_interval_job(self):
        """Crea schedulazione a intervallo (giorni)"""
        days = self.config['interval_days']
        
        self.scheduler.add_job(
            func=self.job_function,
            trigger=IntervalTrigger(days=days),
            id='interval_job',
            replace_existing=True
        )
        
        logger.info(f"Schedulazione a intervallo: ogni {days} giorni")
        return True
    
    def _create_precise_interval_job(self):
        """Crea schedulazione a intervallo preciso (minuti/ore/giorni/secondi)"""
        interval_type = self.config.get('schedule_interval_type', 'minutes')
        interval_value = self.config.get('schedule_interval_value', 30)
        
        # Mappa dei parametri per IntervalTrigger
        trigger_params = {
            'seconds': {'seconds': interval_value},
            'minutes': {'minutes': interval_value},
            'hours': {'hours': interval_value},
            'days': {'days': interval_value}
        }
        
        params = trigger_params.get(interval_type, {'minutes': interval_value})
        
        self.scheduler.add_job(
            func=self.job_function,
            trigger=IntervalTrigger(**params),
            id='interval_precise_job',
            replace_existing=True
        )
        
        logger.info(f"Schedulazione precisa: ogni {interval_value} {interval_type}")
        return True
    
    def _create_cron_job(self):
        """Crea schedulazione con espressione cron"""
        cron_expr = self.config['cron_expression']
        parts = cron_expr.split()
        
        if len(parts) != 5:
            logger.error(f"Espressione cron non valida: {cron_expr}")
            return False
        
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
        
        logger.info(f"Schedulazione cron: {cron_expr}")
        return True
    
    def _log_next_execution(self):
        """Logga la prossima esecuzione programmata"""
        jobs = self.scheduler.get_jobs()
        if jobs and jobs[0].next_run_time:
            next_run = jobs[0].next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Prossima esecuzione: {next_run}")
    
    def get_schedule_description(self):
        """Restituisce descrizione leggibile della schedulazione"""
        if not self.config:
            return "Non configurato"
        
        try:
            return self._build_description()
        except Exception as e:
            logger.error(f"Errore nella descrizione schedulazione: {e}")
            return "Errore configurazione"
    
    def _build_description(self):
        """Costruisce la descrizione in base al tipo di schedulazione"""
        schedule_type = self.config['schedule_type']
        
        descriptions = {
            'monthly': self._get_monthly_description,
            'weekly': self._get_weekly_description,
            'daily': self._get_daily_description,
            'interval': self._get_interval_description,
            'interval_precise': self._get_precise_interval_description,
            'cron': self._get_cron_description
        }
        
        builder = descriptions.get(schedule_type)
        return builder() if builder else "Tipo non riconosciuto"
    
    def _get_monthly_description(self):
        day = self.config['schedule_day']
        time = f"{self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
        return f"Mensile: giorno {day} alle {time}"
    
    def _get_weekly_description(self):
        days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        day_index = self.config['schedule_day']
        day_name = days[day_index] if day_index < 7 else 'Sconosciuto'
        time = f"{self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
        return f"Settimanale: ogni {day_name} alle {time}"
    
    def _get_daily_description(self):
        time = f"{self.config['schedule_hour']}:{self.config['schedule_minute']:02d}"
        return f"Giornaliero: ogni giorno alle {time}"
    
    def _get_interval_description(self):
        days = self.config['interval_days']
        return f"Intervallo: ogni {days} giorni"
    
    def _get_precise_interval_description(self):
        interval_type = self.config.get('schedule_interval_type', 'minutes')
        interval_value = self.config.get('schedule_interval_value', 30)
        
        type_labels = {
            'seconds': 'secondi',
            'minutes': 'minuti',
            'hours': 'ore',
            'days': 'giorni'
        }
        
        unit = type_labels.get(interval_type, 'unità')
        return f"Intervallo preciso: ogni {interval_value} {unit}"
    
    def _get_cron_description(self):
        return f"Cron: {self.config['cron_expression']}"
    
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
        """Restituisce informazioni dettagliate sui job attivi"""
        try:
            jobs = self.scheduler.get_jobs()
            job_info = []
            
            for job in jobs:
                job_info.append({
                    'id': job.id,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                    'func_name': getattr(job.func, '__name__', 'Unknown')
                })
            
            return job_info
            
        except Exception as e:
            logger.error(f"Errore nel recupero info job: {e}")
            return []
    
    def is_running(self):
        """Verifica se lo scheduler è attivo"""
        return self.scheduler.running
    
    def shutdown(self):
        """Ferma lo scheduler in modo sicuro"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Scheduler fermato correttamente")
        except Exception as e:
            logger.error(f"Errore durante shutdown scheduler: {e}")


# Funzioni di utilità per configurazioni comuni
def set_schedule_every_minute(scheduler_manager):
    """Configura esecuzione ogni minuto"""
    _set_precise_interval(scheduler_manager, 'minutes', 1)
    logger.info("Schedulazione impostata: ogni minuto")

def set_schedule_every_hour(scheduler_manager):
    """Configura esecuzione ogni ora"""
    _set_precise_interval(scheduler_manager, 'hours', 1)
    logger.info("Schedulazione impostata: ogni ora")

def set_schedule_every_30_minutes(scheduler_manager):
    """Configura esecuzione ogni 30 minuti"""
    _set_precise_interval(scheduler_manager, 'minutes', 30)
    logger.info("Schedulazione impostata: ogni 30 minuti")

def set_schedule_every_10_seconds(scheduler_manager):
    """Configura esecuzione ogni 10 secondi (per test)"""
    _set_precise_interval(scheduler_manager, 'seconds', 10)
    logger.info("Schedulazione impostata: ogni 10 secondi (TEST)")

def _set_precise_interval(scheduler_manager, interval_type, interval_value):
    """Helper per impostare intervalli precisi"""
    scheduler_manager.config.update({
        'schedule_type': 'interval_precise',
        'schedule_interval_type': interval_type,
        'schedule_interval_value': interval_value
    })
    scheduler_manager.restart_scheduler()