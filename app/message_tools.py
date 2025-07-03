from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
# from flask import jsonify
import json
import time
import functools
import threading

def return_message(success: bool, data: Any = None, message: str = "", 
                      error_code: str = "", status_code: int = 200) -> tuple:
    """Costruisce risposta API standardizzata con gestione migliorata degli errori"""
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    if success:
        if data is not None:
            # Se data è un dizionario, lo merge con response
            if isinstance(data, dict):
                response.update(data)
            else:
                response['data'] = data
        if message:
            response['message'] = message
    else:
        # Gestione degli errori migliorata
        error_info = {
            'message': message or 'Errore sconosciuto',
            'code': error_code or 'UNKNOWN_ERROR'
        }
        
        # Aggiungi suggerimenti per errori comuni
        if 'request-sent' in message.lower() or 'cannotsendrequest' in message.lower():
            error_info['suggestion'] = 'Errore di connessione. Riprova tra qualche secondo.'
            error_info['retry_recommended'] = True
        elif 'connection' in message.lower():
            error_info['suggestion'] = 'Problemi di connessione al server remoto.'
            error_info['retry_recommended'] = True
        elif 'auth' in error_code.lower():
            error_info['suggestion'] = 'Verifica le credenziali di accesso.'
            error_info['retry_recommended'] = False
        
        response['error'] = error_info
        
        if status_code == 200:
            status_code = 400
    # return jsonify(response), status_code
    # return json.dumps(response), status_code
    if success:
        print('Operazione processata con Success = TRUE')
    else:     
        print('Operazione processata con Success = FALSE')
    return response, status_code