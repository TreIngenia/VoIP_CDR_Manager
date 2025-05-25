# integration_cdr_analytics.py
"""
File per integrare CDR Analytics nel progetto FTP Scheduler esistente
Aggiunge l'elaborazione automatica dei file CDR dopo il download con supporto prezzi VoIP
Versione aggiornata con calcolo prezzi basato su configurazione
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
    Configura CDR Analytics nell'applicazione Flask esistente con supporto VoIP
    
    Args:
        app: Istanza Flask
        processor: Istanza FTPProcessor
    """
    
    # Integra CDR Analytics nel processore con configurazione VoIP
    integrate_cdr_analytics_into_processor(processor)
    
    # Aggiungi route Flask per gestire CDR Analytics
    
    @app.route('/cdr_analytics/process/<path:filename>')
    def process_cdr_file(filename):
        """Elabora un singolo file CDR con prezzi VoIP"""
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
                'total_reports': len(reports),
                'voip_pricing_enabled': processor.cdr_analytics.voip_config is not None
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
        """Stato dell'analisi CDR con info VoIP"""
        try:
            analytics_dir = processor.cdr_analytics.analytics_directory
            
            # Conta file per tipo
            individual_reports = len(list(analytics_dir.glob("[0-9]*.json")))
            summary_reports = len(list(analytics_dir.glob("SUMMARY_*.json")))
            
            # Calcola dimensione totale
            total_size = sum(f.stat().st_size for f in analytics_dir.glob("*.json"))
            
            # Info configurazione VoIP
            voip_info = {}
            if processor.cdr_analytics.voip_config:
                voip_info = processor.cdr_analytics.get_voip_categories_info()
            
            return {
                'success': True,
                'analytics_directory': str(analytics_dir),
                'individual_reports': individual_reports,
                'summary_reports': summary_reports,
                'total_reports': individual_reports + summary_reports,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024*1024), 2),
                'voip_pricing_enabled': processor.cdr_analytics.voip_config is not None,
                'voip_configuration': voip_info
            }
        except Exception as e:
            logger.error(f"Errore status CDR analytics: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    @app.route('/cdr_analytics/voip_config')
    def get_voip_config():
        """Restituisce configurazione VoIP per CDR"""
        try:
            if not processor.cdr_analytics.voip_config:
                return {
                    'success': False,
                    'message': 'Configurazione VoIP non disponibile',
                    'voip_enabled': False
                }
            
            config_info = processor.cdr_analytics.get_voip_categories_info()
            return {
                'success': True,
                'voip_enabled': True,
                'configuration': config_info
            }
            
        except Exception as e:
            logger.error(f"Errore recupero config VoIP: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    @app.route('/cdr_analytics/add_custom_mapping', methods=['POST'])
    def add_custom_mapping():
        """Aggiunge mapping personalizzato per tipologie chiamate"""
        try:
            from flask import request
            
            data = request.get_json()
            if not data:
                return {'success': False, 'message': 'Dati non validi'}, 400
            
            categoria = data.get('categoria', '').strip().upper()
            patterns = data.get('patterns', [])
            
            if not categoria or not patterns:
                return {'success': False, 'message': 'Categoria e pattern sono obbligatori'}, 400
            
            # Valida che i pattern siano stringhe
            if not all(isinstance(p, str) for p in patterns):
                return {'success': False, 'message': 'Tutti i pattern devono essere stringhe'}, 400
            
            success = processor.cdr_analytics.add_custom_call_type_mapping(categoria, patterns)
            
            if success:
                return {
                    'success': True,
                    'message': f'Mapping aggiunto per categoria {categoria}',
                    'categoria': categoria,
                    'patterns': patterns
                }
            else:
                return {'success': False, 'message': 'Impossibile aggiungere mapping'}, 500
                
        except Exception as e:
            logger.error(f"Errore aggiunta mapping personalizzato: {e}")
            return {'success': False, 'message': str(e)}, 500
    
    logger.info("🔧 CDR Analytics con supporto VoIP integrato nell'applicazione Flask")


def update_app_py():
    """
    Genera il codice per aggiornare app.py esistente con supporto VoIP
    """
    
    integration_code = '''
# ========== INTEGRAZIONE CDR ANALYTICS CON VOIP ==========
# Aggiungi questo codice nel tuo app.py esistente

# 1. Import aggiuntivi (aggiungi in cima al file)
from integration_cdr_analytics import setup_cdr_analytics

# 2. Dopo la creazione del processore (cerca la riga: processor = FTPProcessor(CONFIG))
# Aggiungi subito dopo:
setup_cdr_analytics(app, processor)

# 3. Opzionale: Aggiorna il template index.html per mostrare info CDR con VoIP
# Aggiungi questo route per info CDR nel dashboard:

@app.route('/cdr_info')
def cdr_info():
    """Informazioni CDR per il dashboard con info VoIP"""
    try:
        if hasattr(processor, 'cdr_analytics'):
            reports = processor.cdr_analytics.list_generated_reports()
            voip_enabled = processor.cdr_analytics.voip_config is not None
            
            voip_info = {}
            if voip_enabled:
                voip_info = processor.cdr_analytics.get_voip_categories_info()
            
            return jsonify({
                'success': True,
                'total_reports': len(reports),
                'recent_reports': reports[:5],  # Ultimi 5 report
                'analytics_enabled': True,
                'voip_pricing_enabled': voip_enabled,
                'voip_configuration': voip_info
            })
        else:
            return jsonify({
                'success': True,
                'analytics_enabled': False,
                'voip_pricing_enabled': False,
                'message': 'CDR Analytics non configurato'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ========== FINE INTEGRAZIONE ==========
'''
    
    return integration_code


def create_enhanced_templates():
    """
    Genera template HTML potenziati con funzionalità CDR e VoIP
    """
    
    # Template per la nuova sezione CDR nel dashboard
    cdr_dashboard_section = '''
<!-- Sezione CDR Analytics con VoIP nel dashboard (aggiungi in templates/index.html) -->
<div class="row mb-4" id="cdr-analytics-section" style="display:none;">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <h5><i class="fas fa-chart-bar"></i> CDR Analytics - Prezzi VoIP</h5>
            </div>
            <div class="card-body">
                <div id="voip-config-info" class="mb-3" style="display:none;">
                    <div class="alert alert-info">
                        <h6><i class="fas fa-phone"></i> Configurazione Prezzi VoIP Attiva</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <small>
                                    <strong>Fisso:</strong> <span id="voip-price-fixed"></span><br>
                                    <strong>Mobile:</strong> <span id="voip-price-mobile"></span><br>
                                    <strong>Valuta:</strong> <span id="voip-currency"></span>
                                </small>
                            </div>
                            <div class="col-md-6">
                                <small>
                                    <strong>Fatturazione:</strong> <span id="voip-unit"></span><br>
                                    <strong>Categorie:</strong> <span id="voip-categories"></span>
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
                
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
                    <button class="btn btn-warning btn-sm" onclick="showVoIPConfig()" id="voip-config-btn">
                        <i class="fas fa-cog"></i> Config VoIP
                    </button>
                    <button class="btn btn-primary btn-sm" onclick="showCustomMappingModal()">
                        <i class="fas fa-plus"></i> Mapping Personalizzato
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Modal per Mapping Personalizzato -->
<div class="modal fade" id="customMappingModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Aggiungi Mapping Personalizzato</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="customMappingForm">
                    <div class="mb-3">
                        <label for="mappingCategory" class="form-label">Categoria</label>
                        <input type="text" class="form-control" id="mappingCategory" 
                               placeholder="es. SMS, VIDEOCHIAMATE, SERVIZI_PREMIUM" required>
                        <div class="form-text">Nome della nuova categoria (lettere maiuscole e underscore)</div>
                    </div>
                    <div class="mb-3">
                        <label for="mappingPatterns" class="form-label">Pattern di Riconoscimento</label>
                        <textarea class="form-control" id="mappingPatterns" rows="3"
                                  placeholder="SMS&#10;MESSAGGIO&#10;SHORT MESSAGE" required></textarea>
                        <div class="form-text">Un pattern per riga. Questi testi verranno cercati nei tipi di chiamata.</div>
                    </div>
                    <div class="mb-3">
                        <small class="text-muted">
                            <strong>Categorie esistenti:</strong> FISSI, MOBILI, FAX, NUMERI_VERDI, INTERNAZIONALI, ALTRO<br>
                            <strong>Nota:</strong> I nuovi mapping useranno il prezzo della categoria più simile.
                        </small>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annulla</button>
                <button type="button" class="btn btn-primary" onclick="submitCustomMapping()">Aggiungi Mapping</button>
            </div>
        </div>
    </div>
</div>

<!-- JavaScript da aggiungere in templates/index.html nella sezione scripts -->
<script>
// Funzioni CDR Analytics con VoIP
function loadCDRInfo() {
    fetch('/cdr_info')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.analytics_enabled) {
                document.getElementById('cdr-analytics-section').style.display = 'block';
                displayCDRReports(data);
                
                // Mostra info VoIP se abilitata
                if (data.voip_pricing_enabled && data.voip_configuration) {
                    displayVoIPConfig(data.voip_configuration);
                }
            }
        })
        .catch(error => console.error('Errore caricamento CDR info:', error));
}

function displayVoIPConfig(voipConfig) {
    const voipSection = document.getElementById('voip-config-info');
    const btn = document.getElementById('voip-config-btn');
    
    if (voipConfig && voipConfig.config) {
        document.getElementById('voip-price-fixed').textContent = 
            voipConfig.config.fixed_price + ' ' + voipConfig.config.currency + '/min';
        document.getElementById('voip-price-mobile').textContent = 
            voipConfig.config.mobile_price + ' ' + voipConfig.config.currency + '/min';
        document.getElementById('voip-currency').textContent = voipConfig.config.currency;
        document.getElementById('voip-unit').textContent = 
            voipConfig.config.unit === 'per_minute' ? 'Al minuto' : 'Al secondo';
        document.getElementById('voip-categories').textContent = voipConfig.categories.join(', ');
        
        voipSection.style.display = 'block';
        btn.classList.replace('btn-warning', 'btn-success');
        btn.innerHTML = '<i class="fas fa-check"></i> VoIP Attivo';
    } else {
        btn.classList.replace('btn-success', 'btn-danger');
        btn.innerHTML = '<i class="fas fa-exclamation"></i> VoIP Non Configurato';
    }
}

function displayCDRReports(data) {
    const container = document.getElementById('cdr-reports-container');
    
    if (data.total_reports === 0) {
        container.innerHTML = '<p class="text-muted">Nessun report CDR generato ancora.</p>';
        return;
    }
    
    let html = `<div class="alert alert-success">
        <strong>Report CDR Disponibili:</strong> ${data.total_reports}
        ${data.voip_pricing_enabled ? 
          '<span class="badge bg-success ms-2"><i class="fas fa-phone"></i> Prezzi VoIP Attivi</span>' : 
          '<span class="badge bg-warning ms-2"><i class="fas fa-exclamation"></i> Solo Prezzi Originali</span>'
        }
    </div>`;
    
    if (data.recent_reports && data.recent_reports.length > 0) {
        html += '<div class="table-responsive"><table class="table table-sm">';
        html += '<thead><tr><th>File</th><th>Tipo</th><th>Dimensione</th><th>Creato</th><th>Azioni</th></tr></thead><tbody>';
        
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
                <td>
                    ${isSummary ? 
                      '<span class="badge bg-warning">Globale</span>' : 
                      '<span class="badge bg-primary">Contratto</span>'
                    }
                    ${data.voip_pricing_enabled ? 
                      '<br><small class="text-success"><i class="fas fa-phone"></i> VoIP</small>' : 
                      '<br><small class="text-muted">Originale</small>'
                    }
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

function showVoIPConfig() {
    fetch('/cdr_analytics/voip_config')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.voip_enabled) {
                const config = data.configuration;
                let configHtml = `
                    <h6>Configurazione Prezzi VoIP</h6>
                    <p><strong>Valuta:</strong> ${config.config.currency}</p>
                    <p><strong>Unità:</strong> ${config.config.unit === 'per_minute' ? 'Al minuto' : 'Al secondo'}</p>
                    <p><strong>Prezzo Fisso:</strong> ${config.config.fixed_price} ${config.config.currency}</p>
                    <p><strong>Prezzo Mobile:</strong> ${config.config.mobile_price} ${config.config.currency}</p>
                    
                    <h6 class="mt-3">Categorie e Prezzi</h6>
                    <ul class="list-group">
                `;
                
                Object.entries(config.pricing).forEach(([cat, price]) => {
                    configHtml += `<li class="list-group-item d-flex justify-content-between">
                        <span>${cat}</span>
                        <span class="badge bg-primary">${price} ${config.config.currency}</span>
                    </li>`;
                });
                
                configHtml += '</ul>';
                
                showAlert('info', 'Configurazione VoIP', configHtml);
            } else {
                showAlert('warning', 'VoIP Non Configurato', 
                    'La configurazione VoIP non è disponibile. Configura i prezzi VoIP nelle impostazioni dell\'applicazione.');
            }
        })
        .catch(error => {
            showAlert('danger', 'Errore', 'Errore nel recupero configurazione VoIP: ' + error);
        });
}

function showCustomMappingModal() {
    new bootstrap.Modal(document.getElementById('customMappingModal')).show();
}

function submitCustomMapping() {
    const categoria = document.getElementById('mappingCategory').value.trim().toUpperCase();
    const patternsText = document.getElementById('mappingPatterns').value.trim();
    
    if (!categoria || !patternsText) {
        showAlert('warning', 'Attenzione', 'Compila tutti i campi obbligatori.');
        return;
    }
    
    const patterns = patternsText.split('\n').map(p => p.trim()).filter(p => p);
    
    if (patterns.length === 0) {
        showAlert('warning', 'Attenzione', 'Inserisci almeno un pattern.');
        return;
    }
    
    fetch('/cdr_analytics/add_custom_mapping', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            categoria: categoria,
            patterns: patterns
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', 'Successo', 
                `Mapping aggiunto per categoria ${data.categoria}: ${data.patterns.join(', ')}`);
            bootstrap.Modal.getInstance(document.getElementById('customMappingModal')).hide();
            document.getElementById('customMappingForm').reset();
        } else {
            showAlert('danger', 'Errore', data.message);
        }
    })
    .catch(error => {
        showAlert('danger', 'Errore', 'Errore nella richiesta: ' + error);
    });
}

function refreshCDRInfo() {
    loadCDRInfo();
}

function showAlert(type, title, message) {
    // Implementazione alert personalizzata (da definire nel template principale)
    alert(`${title}: ${message}`);
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
    Crea script di test per CDR Analytics con VoIP
    """
    
    test_script = '''#!/usr/bin/env python3
"""
Script di test per CDR Analytics con supporto VoIP
Testa l'elaborazione di file CDR con calcolo prezzi VoIP
"""

import json
import sys
from pathlib import Path
from cdr_analytics import CDRAnalytics, process_cdr_standalone

def test_cdr_analytics_with_voip():
    """Testa CDR Analytics con configurazione VoIP"""
    
    print("🧪 Test CDR Analytics con Prezzi VoIP")
    print("=" * 50)
    
    # Configurazione VoIP di test
    test_voip_config = {
        'voip_price_fixed_final': 0.02,      # 2 centesimi al minuto per fisso
        'voip_price_mobile_final': 0.15,     # 15 centesimi al minuto per mobile
        'voip_currency': 'EUR',
        'voip_price_unit': 'per_minute'
    }
    
    print("💰 Configurazione VoIP di test:")
    print(f"   Fisso: {test_voip_config['voip_price_fixed_final']} {test_voip_config['voip_currency']}/min")
    print(f"   Mobile: {test_voip_config['voip_price_mobile_final']} {test_voip_config['voip_currency']}/min")
    print(f"   Unità: {test_voip_config['voip_price_unit']}")
    
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
        print(f"📊 Elaborazione file con VoIP: {test_file}")
        result = process_cdr_standalone(str(test_file), "test_output", voip_config=test_voip_config)
        
        if result['success']:
            print("✅ Test completato con successo!")
            print(f"📈 Contratti elaborati: {result['total_contracts']}")
            print(f"📁 File generati: {len(result['generated_files'])}")
            print(f"📞 Tipi chiamata trovati: {', '.join(result['call_types_found'])}")
            print(f"💰 Prezzi VoIP abilitati: {result.get('voip_pricing_enabled', False)}")
            
            if 'voip_config_summary' in result:
                voip_summary = result['voip_config_summary']
                print(f"\n💰 Configurazione VoIP applicata:")
                print(f"   Valuta: {voip_summary['currency']}")
                print(f"   Unità: {voip_summary['unit']}")
                print(f"   Categorie: {', '.join(voip_summary['categories'])}")
            
            print("\\n📄 File generati:")
            for i, file_path in enumerate(result['generated_files'], 1):
                print(f"   {i}. {file_path}")
                
                # Mostra anteprima del primo file
                if i == 1:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            preview_data = json.load(f)
                        
                        print(f"\\n👀 Anteprima {Path(file_path).name}:")
                        summary = preview_data.get('summary', {})
                        print(f"   Contratto: {summary.get('codice_contratto')}")
                        print(f"   Comune: {summary.get('cliente_finale_comune')}")
                        print(f"   Chiamate totali: {summary.get('totale_chiamate')}")
                        print(f"   Durata totale: {summary.get('durata_totale_minuti')} min")
                        print(f"   Costo originale: €{summary.get('costo_totale_euro', 0)}")
                        print(f"   Costo cliente VoIP: €{summary.get('costo_cliente_totale_euro', 0)}")
                        
                        # Mostra breakdown categorie se disponibile
                        if 'categoria_breakdown' in summary:
                            print("\\n📊 Breakdown per categoria:")
                            for cat, data in summary['categoria_breakdown'].items():
                                print(f"   {cat}: {data['chiamate']} chiamate, €{data['costo_cliente_euro']}")
                        
                    except Exception as e:
                        print(f"   ⚠️ Errore anteprima: {e}")
            
        else:
            print(f"❌ Test fallito: {result['message']}")
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")

def test_custom_mapping():
    """Testa mapping personalizzato"""
    print("\\n🧪 Test Mapping Personalizzato")
    print("=" * 30)
    
    # Configurazione VoIP di test
    test_voip_config = {
        'voip_price_fixed_final': 0.02,
        'voip_price_mobile_final': 0.15,
        'voip_currency': 'EUR',
        'voip_price_unit': 'per_minute'
    }
    
    # Crea istanza CDR Analytics
    analytics = CDRAnalytics("test_output", voip_config=test_voip_config)
    
    # Aggiungi mapping personalizzato
    analytics.add_custom_call_type_mapping('SMS', ['SMS', 'MESSAGGIO', 'SHORT MESSAGE'])
    analytics.add_custom_call_type_mapping('VIDEOCHIAMATE', ['VIDEO', 'VIDEOCALL', 'VIDEOCHIAMATA'])
    
    # Testa classificazione
    test_types = [
        'SMS PREMIUM',
        'VIDEOCALL HD',
        'CELLULARE',
        'INTERRURBANE URBANE',
        'NUMERO VERDE',
        'INTERNAZIONALE'
    ]
    
    print("🔍 Test classificazione tipi di chiamata:")
    for tipo in test_types:
        categoria = analytics.voip_config.classify_call_type(tipo)
        prezzo = analytics.voip_config.get_price_for_category(categoria)
        print(f"   '{tipo}' -> {categoria} (€{prezzo}/min)")

if __name__ == "__main__":
    test_cdr_analytics_with_voip()
    test_custom_mapping()
'''
    
    return test_script


def main():
    """Funzione principale per setup CDR Analytics con VoIP"""
    
    print("🚀 Setup CDR Analytics con Prezzi VoIP per FTP Scheduler")
    print("=" * 60)
    
    # Crea file necessari
    current_dir = Path.cwd()
    
    # 1. Salva script di test
    test_script_path = current_dir / "test_cdr_analytics_voip.py"
    with open(test_script_path, 'w', encoding='utf-8') as f:
        f.write(create_test_script())
    print(f"✅ Script di test VoIP creato: {test_script_path}")
    
    # 2. Crea directory per analytics se non esiste
    analytics_dir = current_dir / "output" / "cdr_analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Directory analytics creata: {analytics_dir}")
    
    # 3. Mostra codice di integrazione
    print("\\n📋 ISTRUZIONI PER L'INTEGRAZIONE:")
    print("=" * 50)
    print("1. Sostituisci il file 'cdr_analytics.py' con la nuova versione")
    print("2. Sostituisci il file 'integration_cdr_analytics.py' con la nuova versione")
    print("3. Modifica il file 'app.py' aggiungendo questo codice:")
    print()
    print(update_app_py())
    
    print("\\n🎨 TEMPLATE HTML AGGIORNATO:")
    print("=" * 35)
    print("Aggiungi questa sezione nel template templates/index.html:")
    print("(La sezione è lunga, vedi il codice generato)")
    
    print("\\n🧪 TEST:")
    print("=" * 10)
    print("Per testare CDR Analytics con VoIP:")
    print("python test_cdr_analytics_voip.py")
    
    print("\\n🎉 Setup completato!")
    print("Una volta integrato, CDR Analytics processerà automaticamente")
    print("tutti i file CDR scaricati applicando i prezzi VoIP configurati.")
    print("\\nFunzionalità aggiunte:")
    print("• Calcolo automatico costi con prezzi VoIP")
    print("• Campo 'costo_cliente_euro' in tutti i report")
    print("• Classificazione automatica per categoria (FISSI, MOBILI, etc.)")
    print("• Mapping personalizzato per nuove tipologie")
    print("• Dashboard con info configurazione VoIP")
    print("• API per gestione mapping personalizzati")

if __name__ == "__main__":
    main()