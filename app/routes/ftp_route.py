from logger_config import get_logger
from ftp_downloader import FTPDownloader
from flask import jsonify

logger = get_logger(__name__)
# try:
#     from dotenv import load_dotenv
#     import os
#     load_dotenv()  # Carica variabili dal file .env
#     print("📁 File .env caricato")
#     FTP_HOST=os.getenv('FTP_HOST')
#     FTP_PORT=int(os.getenv('FTP_PORT'))
#     FTP_USER=os.getenv('FTP_USER')
#     FTP_PASSWORD=os.getenv('FTP_PASSWORD')
#     FTP_DIRECTORY=os.getenv('FTP_DIRECTORY')
#     SPECIFIC_FILENAME=os.getenv('SPECIFIC_FILENAME')
#     OUTPUT_DIRECTORY=os.getenv('OUTPUT_DIRECTORY')
    
# except ImportError:
#     print("⚠️ python-dotenv non installato - usando solo variabili d'ambiente del sistema")
    
def ftp_routes(app, secure_config):
    @app.route('/test_ftp')
    def test_ftp():
        ftp = FTPDownloader(secure_config)
        downloader = ftp.runftp("*", True)
        return downloader
        # downloader = FTPDownloader(FTP_HOST, FTP_USER, FTP_PASSWORD, FTP_PORT)
        # # """Test connessione FTP"""
        # try:
        #     # Connettiti
        #     if not downloader.connetti():
        #         return
            
        #     # Scarica i file per template
        #     file_scaricati = downloader.scarica_per_template(
        #         template="*",
        #         directory_ftp=FTP_DIRECTORY,
        #         cartella_locale=OUTPUT_DIRECTORY,
        #         data=None,
        #         test=True
        #     )

        #     server = OrderedDict([
        #         ("FTP_HOST", FTP_HOST),
        #         ("FTP_USER", FTP_USER),
        #         ("FTP_PASSWORD", "*************"),
        #         ("FTP_PORT", FTP_PORT),
        #         ("FTP_DIRECTORY", FTP_DIRECTORY)
        #     ])

        #     response_data = OrderedDict([
        #         ("success", True),
        #         ("server", server),
        #         ("files", file_scaricati)
        #     ])

        #     if file_scaricati:
        #         print(f"\n🎉 Download completato! File scaricati:")
        #         for f in file_scaricati:
        #             print(f"  ✓ {f}")
        #         return jsonify({'ftp_connection': True, 'success': True, 'files': file_scaricati})
        #     else:
        #         logger.error(f"Errore test FTP: Nessun file presente nell'FTP.'")
        #     return jsonify({'ftp_connection': True, 'success': False, 'message': 'Nessun file presente nell\'FTP.'})
        
        # except Exception as e:
        #     logger.error(f"Errore test FTP: {e}")
        #     return jsonify({'ftp_connection': False, 'success': False, 'message': str(e)})

        # finally:
        #     # Disconnetti sempre
        #     downloader.disconnetti()


    @app.route('/test_ftp_template')
    def test_ftp_template():
        downloader = FTPDownloader.runftp(SPECIFIC_FILENAME, True)
        return downloader
        # downloader = FTPDownloader(FTP_HOST, FTP_USER, FTP_PASSWORD, FTP_PORT)
        # # """Test connessione FTP"""
        # try:
        #     # Connettiti
        #     if not downloader.connetti():
        #         return
            
        #     # Scarica i file per template
        #     file_scaricati = downloader.scarica_per_template(
        #         template=SPECIFIC_FILENAME,
        #         directory_ftp=FTP_DIRECTORY,
        #         cartella_locale=OUTPUT_DIRECTORY,
        #         data=None,
        #         test=True
        #     )

        #     # Mostra il risultato
        #     if file_scaricati:
        #         print(f"\n🎉 Download completato! File scaricati:")
        #         for f in file_scaricati:
        #             print(f"  ✓ {f}")
        #         return jsonify({'ftp_connection': True, 'success': True, 'files': file_scaricati})
        #     else:
        #         logger.error(f"Errore test FTP: Nessun file presente nell'FTP.'")
        #     return jsonify({'ftp_connection': True, 'success': False, 'message': 'Nessun file presente nell\'FTP.'})
        
        # except Exception as e:
        #     logger.error(f"Errore test FTP: {e}")
        #     return jsonify({'ftp_connection': False, 'success': False, 'message': str(e)})

        # finally:
        #     # Disconnetti sempre
        #     downloader.disconnetti()


    @app.route('/test_ftp_template/')
    @app.route('/test_ftp_template/<string:get_template>')
    def test_ftp_template_manual(get_template="*"):
        downloader = FTPDownloader.runftp(get_template, True)
        return downloader

    @app.route('/download_ftp_template')
    def download_ftp_template():
        downloader = FTPDownloader.runftp(SPECIFIC_FILENAME, False)
        return downloader
        # downloader = FTPDownloader(FTP_HOST, FTP_USER, FTP_PASSWORD, FTP_PORT)
        # # """Test connessione FTP"""
        # try:
        #     # Connettiti
        #     if not downloader.connetti():
        #         return
            
        #     # Scarica i file per template
        #     file_scaricati = downloader.scarica_per_template(
        #         template=SPECIFIC_FILENAME,
        #         directory_ftp=FTP_DIRECTORY,
        #         cartella_locale=OUTPUT_DIRECTORY,
        #         data=None,
        #         test=None
        #     )

        #     # Mostra il risultato
        #     if file_scaricati:
        #         print(f"\n🎉 Download completato! File scaricati:")
        #         for f in file_scaricati:
        #             print(f"  ✓ {f}")
        #         return jsonify({'ftp_connection': True, 'success': True, 'files': file_scaricati})
        #     else:
        #         logger.error(f"Errore test FTP: Nessun file presente nell'FTP.'")
        #     return jsonify({'ftp_connection': True, 'success': False, 'message': 'Nessun file presente nell\'FTP.'})
        
        # except Exception as e:
        #     logger.error(f"Errore test FTP: {e}")
        #     return jsonify({'ftp_connection': False, 'success': False, 'message': str(e)})

        # finally:
        #     # Disconnetti sempre
        #     downloader.disconnetti()

    @app.route('/manual_run')
    def manual_run():
        """Esecuzione manuale del processo con gestione serializzazione JSON corretta"""
        try:

            # ✅ Istanzia il downloader
            downloader = FTPDownloader(secure_config)
            
            # ✅ Chiama il metodo sull'istanza
            result = downloader.process_files()
            return(result)
            # # ✅ PULIZIA RISULTATO PER JSON SERIALIZATION
            # if isinstance(result, dict):
            #     # Rimuovi eventuali riferimenti a oggetti non serializzabili
            #     clean_result = clean_for_json_serialization(result)
            #     return jsonify(clean_result)
            # else:
            #     # Fallback se result non è un dict
            #     return jsonify({
            #         'success': True,
            #         'message': 'Processo completato',
            #         'details': str(result)
            #     })
                
        except Exception as e:
            logger.error(f"Errore esecuzione manuale: {e}")
            return jsonify({
                'success': False, 
                'message': str(e),
                'error_type': type(e).__name__
            })