# integration_cdr_analytics.py
"""
File per integrare CDR Analytics nel progetto FTP Scheduler esistente
Aggiunge l'elaborazione automatica dei file CDR dopo il download
"""

import sys
import os
from pathlib import Path

# Aggiungi il modulo CDR al path se non già presente
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from cdr_analytics import CDRAnalytics, integrate_cdr_analytics_into_processor
import logging

logger = logging.getLogger(__name__)

def setup_cdr_analytics(app, processor):
    """
    Configura CDR Analytics nell'applicazione Flask esistente
    
    Args:
        app: Istanza Flask
        processor: Istanza FTPProcessor
    """
    
    # Integra CDR Analytics nel processore
    integrate_cdr_analytics_into_processor(processor)
    
    # Aggiungi route Flask per gestire CDR Analytics
    
    @app.route('/cdr_analytics/process/<path:filename>')
    def process_cdr_file(filename):
        """Elabora un singolo file CDR"""
        try:
            file_path = Path(processor.config['output_directory']) / filename
            
            if not file_path.exists():
                return {'success': False, 'message': 'File non trovato'}, 404
            
            result = processor.cdr_analytics.process_cdr_file(str(file_path))
            return result
            
        except Exception as e:
            logger.error(f"Errore elaborazione CDR via web: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    @app.route('/cdr_analytics/reports')
    def list_cdr_reports():
        """Lista tutti i report CDR generati"""
        try:
            reports = processor.cdr_analytics.list_generated_reports()
            return {
                'success': True,
                'reports': reports,
                'total_reports': len(reports)
            }
        except Exception as e:
            logger.error(f"Errore listing report CDR: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    @app.route('/cdr_analytics/reports/<path:filename>')
    def download_cdr_report(filename):
        """Download di un report CDR specifico"""
        try:
            from flask import send_file
            
            report_path = processor.cdr_analytics.analytics_directory / filename
            
            if not report_path.exists():
                return {'success': False, 'message': 'Report non trovato'}, 404
            
            return send_file(
                report_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/json'
            )
            
        except Exception as e:
            logger.error(f"Errore download report CDR: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    @app.route('/cdr_analytics/status')
    def cdr_analytics_status():
        """Stato dell'analisi CDR"""
        try:
            analytics_dir = processor.cdr_analytics.analytics_directory
            
            # Conta file per tipo
            individual_reports = len(list(analytics_dir.glob("[0-9]*.json")))
            summary_reports = len(list(analytics_dir.glob("SUMMARY_*.json")))
            
            # Calcola dimensione totale
            total_size = sum(f.stat().st_size for f in analytics_dir.glob("*.json"))
            
            return {
                'success': True,
                'analytics_directory': str(analytics_dir),
                'individual_reports': individual_reports,
                'summary_reports': summary_reports,
                'total_reports': individual_reports + summary_reports,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024*1024), 2)
            }
        except Exception as e:
            logger.error(f"Errore status CDR analytics: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    logger.info("🔧 CDR Analytics integrato nell'applicazione Flask")


def update_app_py():
    """
    Genera il codice per aggiornare app.py esistente
    """
    
    integration_code = '''
# ========== INTEGRAZIONE CDR ANALYTICS ==========
# Aggiungi questo codice nel tuo app.py esistente

# 1. Import aggiuntivi (aggiungi in cima al file)
from integration_cdr_analytics import setup_cdr_analytics

# 2. Dopo la creazione del processore (cerca la riga: processor = FTPProcessor(CONFIG))
# Aggiungi subito dopo:
setup_cdr_analytics(app, processor)

# 3. Opzionale: Aggiorna il template index.html per mostrare info CDR
# Aggiungi questo route per info CDR nel dashboard:

@app.route('/cdr_info')
def cdr_info():
    """Informazioni CDR per il dashboard"""
    try:
        if hasattr(processor, 'cdr_analytics'):
            reports = processor.cdr_analytics.list_generated_reports()
            return jsonify({
                'success': True,
                'total_reports': len(reports),
                'recent_reports': reports[:5],  # Ultimi 5 report
                'analytics_enabled': True
            })
        else:
            return jsonify({
                'success': True,
                'analytics_enabled': False,
                'message': 'CDR Analytics non configurato'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ========== FINE INTEGRAZIONE ==========
'''
    
    return integration_code


def create_enhanced_templates():
    """
    Genera template HTML potenziati con funzionalità CDR
    """
    
    # Template per la nuova sezione CDR nel dashboard
    cdr_dashboard_section = '''
<!-- Sezione CDR Analytics nel dashboard (aggiungi in templates/index.html) -->
<div class="row mb-4" id="cdr-analytics-section" style="display:none;">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-chart-bar"></i> CDR Analytics - Ultimi Report</h5>
            </div>
            <div class="card-body">
                <div id="cdr-reports-container">
                    <p class="text-muted">Caricamento report CDR...</p>
                </div>
                <div class="mt-3">
                    <a href="/cdr_analytics/reports" class="btn btn-info btn-sm" target="_blank">
                        <i class="fas fa-list"></i> Tutti i Report
                    </a>
                    <button class="btn btn-success btn-sm" onclick="refreshCDRInfo()">
                        <i class="fas fa-sync"></i> Aggiorna
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- JavaScript da aggiungere in templates/index.html nella sezione scripts -->
<script>
// Funzioni CDR Analytics
function loadCDRInfo() {
    fetch('/cdr_info')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.analytics_enabled) {
                document.getElementById('cdr-analytics-section').style.display = 'block';
                displayCDRReports(data);
            }
        })
        .catch(error => console.error('Errore caricamento CDR info:', error));
}

function displayCDRReports(data) {
    const container = document.getElementById('cdr-reports-container');
    
    if (data.total_reports === 0) {
        container.innerHTML = '<p class="text-muted">Nessun report CDR generato ancora.</p>';
        return;
    }
    
    let html = `<div class="alert alert-info">
        <strong>Report CDR Disponibili:</strong> ${data.total_reports}
    </div>`;
    
    if (data.recent_reports && data.recent_reports.length > 0) {
        html += '<div class="table-responsive"><table class="table table-sm">';
        html += '<thead><tr><th>File</th><th>Dimensione</th><th>Creato</th><th>Azioni</th></tr></thead><tbody>';
        
        data.recent_reports.forEach(report => {
            const sizeMB = (report.size_bytes / (1024*1024)).toFixed(2);
            const createdDate = new Date(report.created).toLocaleString('it-IT');
            const isSummary = report.is_summary;
            
            html += `<tr class="${isSummary ? 'table-warning' : ''}">
                <td>
                    <i class="fas fa-${isSummary ? 'chart-pie' : 'file-alt'}"></i>
                    ${report.filename}
                    ${isSummary ? '<span class="badge bg-warning">Summary</span>' : ''}
                </td>
                <td>${sizeMB} MB</td>
                <td>${createdDate}</td>
                <td>
                    <a href="/cdr_analytics/reports/${report.filename}" class="btn btn-sm btn-outline-primary" title="Download">
                        <i class="fas fa-download"></i>
                    </a>
                </td>
            </tr>`;
        });
        
        html += '</tbody></table></div>';
        
        if (data.total_reports > 5) {
            html += `<p class="text-muted">Mostrati 5 di ${data.total_reports} report totali.</p>`;
        }
    }
    
    container.innerHTML = html;
}

function refreshCDRInfo() {
    loadCDRInfo();
}

// Carica info CDR all'avvio
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(loadCDRInfo, 1000); // Carica dopo 1 secondo
});
</script>
'''
    
    return cdr_dashboard_section


def create_test_script():
    """
    Crea script di test per CDR Analytics
    """
    
    test_script = '''#!/usr/bin/env python3
"""
Script di test per CDR Analytics
Testa l'elaborazione di file CDR con dati di esempio
"""

import json
import sys
from pathlib import Path
from cdr_analytics import CDRAnalytics, process_cdr_standalone

def test_cdr_analytics():
    """Testa CDR Analytics con un file esistente"""
    
    print("🧪 Test CDR Analytics")
    print("=" * 50)
    
    # Cerca file CDR nella directory output
    output_dir = Path("output")
    cdr_files = []
    
    if output_dir.exists():
        # Cerca file JSON che potrebbero essere CDR
        for json_file in output_dir.glob("*.json"):
            if any(keyword in json_file.name.upper() for keyword in ['CDR', 'RIV']):
                cdr_files.append(json_file)
    
    if not cdr_files:
        print("❌ Nessun file CDR trovato nella directory output/")
        print("💡 Esegui prima il download FTP per ottenere file CDR")
        return
    
    # Testa il primo file trovato
    test_file = cdr_files[0]
    
    try:
        print(f"📊 Elaborazione file: {test_file}")
        result = process_cdr_standalone(str(test_file), "test_output")
        
        if result['success']:
            print("✅ Test completato con successo!")
            print(f"📈 Contratti elaborati: {result['total_contracts']}")
            print(f"📁 File generati: {len(result['generated_files'])}")
            print(f"📞 Tipi chiamata trovati: {', '.join(result['call_types_found'])}")
            
            print("\\n📄 File generati:")
            for i, file_path in enumerate(result['generated_files'], 1):
                print(f"   {i}. {file_path}")
                
                # Mostra anteprima del primo file
                if i == 1:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            preview_data = json.load(f)
                        
                        print(f"\\n👀 Anteprima {Path(file_path).name}:")
                        print(f"   Contratto: {preview_data['summary']['codice_contratto']}")
                        print(f"   Comune: {preview_data['summary']['cliente_finale_comune']}")
                        print(f"   Chiamate totali: {preview_data['summary']['totale_chiamate']}")
                        print(f"   Durata totale: {preview_data['summary']['durata_totale_minuti']} min")
                        print(f"   Costo totale: €{preview_data['summary']['costo_totale_euro']}")
                        
                    except Exception as e:
                        print(f"   ⚠️ Errore anteprima: {e}")
            
        else:
            print(f"❌ Test fallito: {result['message']}")
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")

if __name__ == "__main__":
    test_cdr_analytics()
'''
    
    return test_script


def main():
    """Funzione principale per setup CDR Analytics"""
    
    print("🚀 Setup CDR Analytics per FTP Scheduler")
    print("=" * 50)
    
    # Crea file necessari
    current_dir = Path.cwd()
    
    # 1. Salva script di test
    test_script_path = current_dir / "test_cdr_analytics.py"
    with open(test_script_path, 'w', encoding='utf-8') as f:
        f.write(create_test_script())
    print(f"✅ Script di test creato: {test_script_path}")
    
    # 2. Crea directory per analytics se non esiste
    analytics_dir = current_dir / "output" / "cdr_analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Directory analytics creata: {analytics_dir}")
    
    # 3. Mostra codice di integrazione
    print("\n📋 ISTRUZIONI PER L'INTEGRAZIONE:")
    print("=" * 50)
    print("1. Salva il modulo 'cdr_analytics.py' nella directory del progetto")
    print("2. Salva il file 'integration_cdr_analytics.py' nella directory del progetto")
    print("3. Modifica il file 'app.py' aggiungendo questo codice:")
    print()
    print(update_app_py())
    
    print("\n🎨 TEMPLATE HTML AGGIORNATO:")
    print("=" * 30)
    print("Aggiungi questa sezione nel template templates/index.html:")
    print(create_enhanced_templates())
    
    print("\n🧪 TEST:")
    print("=" * 10)
    print("Per testare CDR Analytics:")
    print("python test_cdr_analytics.py")
    
    print("\n🎉 Setup completato!")
    print("Una volta integrato, CDR Analytics processerà automaticamente")
    print("tutti i file CDR scaricati e genererà report dettagliati.")

if __name__ == "__main__":
    main()