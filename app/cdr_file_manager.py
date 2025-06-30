from pathlib import Path
from typing import List, Union
import logging

logger = logging.getLogger(__name__)

def get_files_by_extension(directory: Union[str, Path], extension: str, recursive: bool = False) -> List[Path]:
    """
    Legge tutti i file con una determinata estensione da una directory.
    
    Args:
        directory (str | Path): Percorso della directory da analizzare
        extension (str): Estensione dei file da cercare (es: '.json', 'json', '*.json')
        recursive (bool): Se True, cerca anche nelle sottodirectory (default: False)
    
    Returns:
        List[Path]: Lista di oggetti Path dei file trovati
        
    Raises:
        FileNotFoundError: Se la directory non esiste
        PermissionError: Se non si hanno permessi di lettura sulla directory
        
    Examples:
        >>> files = get_files_by_extension('./output', '.json')
        >>> files = get_files_by_extension('/path/to/data', 'cdr', recursive=True)
        >>> files = get_files_by_extension(Path('./reports'), '*.pdf')
    """
    try:
        # Normalizza il percorso della directory
        directory_path = Path(directory)
        
        # Verifica che la directory esista
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory non trovata: {directory_path}")
        
        if not directory_path.is_dir():
            raise NotADirectoryError(f"Il percorso non è una directory: {directory_path}")
        
        # Normalizza l'estensione
        extension = extension.strip()
        if extension.startswith('*.'):
            # Rimuove il wildcard se presente (es: '*.json' -> '.json')
            extension = extension[1:]
        elif not extension.startswith('.'):
            # Aggiunge il punto se mancante (es: 'json' -> '.json')
            extension = f'.{extension}'
        
        # Pattern di ricerca
        if recursive:
            pattern = f'**/*{extension}'
            files = list(directory_path.glob(pattern))
        else:
            pattern = f'*{extension}'
            files = list(directory_path.glob(pattern))
        
        # Filtra solo i file (esclude directory)
        files = [f for f in files if f.is_file()]
        
        # Ordina per nome file
        files.sort(key=lambda x: x.name.lower())
        
        logger.info(f"Trovati {len(files)} file con estensione '{extension}' in {directory_path}")
        if len(files) > 0:
            logger.debug(f"Primo file: {files[0].name}")
            logger.debug(f"Ultimo file: {files[-1].name}")
        
        return files
        
    except (FileNotFoundError, NotADirectoryError):
        # Re-raise questi errori specifici
        raise
    except PermissionError as e:
        logger.error(f"Permessi insufficienti per accedere a {directory_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Errore durante la lettura dei file in {directory_path}: {e}")
        raise


def get_recent_files_by_extension(directory: Union[str, Path], extension: str, 
                                 max_files: int = None, recursive: bool = False) -> List[Path]:
    """
    Variante che restituisce i file più recenti per data di modifica.
    
    Args:
        directory (str | Path): Percorso della directory da analizzare
        extension (str): Estensione dei file da cercare
        max_files (int): Numero massimo di file da restituire (None = tutti)
        recursive (bool): Se True, cerca anche nelle sottodirectory
    
    Returns:
        List[Path]: Lista di file ordinati per data di modifica (più recenti primi)
    """
    try:
        files = get_files_by_extension(directory, extension, recursive)
        
        # Ordina per data di modifica (più recenti prima)
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Limita il numero se richiesto
        if max_files is not None and max_files > 0:
            files = files[:max_files]
        
        logger.info(f"Restituiti {len(files)} file più recenti")
        return files
        
    except Exception as e:
        logger.error(f"Errore durante la lettura dei file recenti: {e}")
        raise


# Esempi di utilizzo:
if __name__ == "__main__":
    # Configurazione logging per test
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Esempio 1: File JSON nella directory output
        # json_files = get_files_by_extension('./output', '.json')
        # print(f"File JSON trovati: {len(json_files)}")
        
        # Esempio 2: File CDR ricorsivamente
        cdr_files = get_files_by_extension('./output', '.cdr', recursive=False)
        print(cdr_files)
        print(f"File CDR trovati: {len(cdr_files)}")
        
        # Esempio 3: Ultimi 5 file JSON modificati
        recent_files = get_recent_files_by_extension('./output', 'json', max_files=5)
        print(f"File recenti: {len(recent_files)}")
        
        # Mostra i percorsi per il test
        for file_path in cdr_files:  # Primi 3 file
            print(f"  - {file_path}")
            
    except Exception as e:
        print(f"Errore: {e}")