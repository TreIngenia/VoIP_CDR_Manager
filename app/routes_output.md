# 📋 Elenco Route Estratti

## 📊 Riepilogo

- **File analizzati**: 9
- **Route totali**: 103
- **Data estrazione**: 23/06/2025 10:41:34

## 📑 Indice dei File

- [cdr_categories_routes.py](#cdr_categories_routes-py) (16 route)
- [contratti_routes.py](#contratti_routes-py) (12 route)
- [default_routes.py](#default_routes-py) (24 route)
- [fatture_routes copy.py](#fatture_routes copy-py) (2 route)
- [fatture_routes.py](#fatture_routes-py) (6 route)
- [listino_routes copy.py](#listino_routes copy-py) (9 route)
- [listino_routes.py](#listino_routes-py) (9 route)
- [menu_routes.py](#menu_routes-py) (3 route)
- [odoo_routes.py](#odoo_routes-py) (22 route)

## 📁 Route per File

### cdr_categories_routes.py

**Numero di route**: 16

| Route |
|-------|
| `/api/categories` |
| `/api/categories/<category_name>` |
| `/api/categories/bulk-update-markup` |
| `/api/categories/conflicts` |
| `/api/categories/export` |
| `/api/categories/global-markup` |
| `/api/categories/health` |
| `/api/categories/import` |
| `/api/categories/pricing-preview` |
| `/api/categories/reset-defaults` |
| `/api/categories/statistics` |
| `/api/categories/test-classification` |
| `/api/categories/validate` |
| `/cdr_categories_dashboard` |
| `/cdr_categories_edit` |
| `/cdr_categories_new` |

### contratti_routes.py

**Numero di route**: 12

| Route |
|-------|
| `/api/cdr/contract_type` |
| `/api/cdr/contracts_config` |
| `/api/cdr/extract_contracts` |
| `/api/cdr/update_contract` |
| `/api/contracts/datatable/ajax` |
| `/api/contracts/datatable/serverside` |
| `/api/contracts/datatable/summary` |
| `/api/contracts/datatable/test` |
| `/api/contracts/info` |
| `/api/contracts/process` |
| `/api/contracts/process/status` |
| `/gestione_contratti` |

### default_routes.py

**Numero di route**: 24

| Route |
|-------|
| `/` |
| `/api/cdr/categories_summary` |
| `/api/cdr/process_with_categories/<path:filename>` |
| `/api/cdr/reports_with_categories` |
| `/api/cdr/test_category_matching` |
| `/api/voip/calculate` |
| `/api/voip/update_prices` |
| `/cdr_analytics/process_all` |
| `/cdr_analytics/report_details/<path:filename>` |
| `/cdr_dashboard` |
| `/config` |
| `/default_page` |
| `/gestione_contratti` |
| `/health` |
| `/list_ftp_files` |
| `/logs` |
| `/manual_run` |
| `/pattern_examples` |
| `/quick_schedule/<schedule_type>` |
| `/schedule_info` |
| `/status` |
| `/status_page` |
| `/test_ftp` |
| `/test_pattern` |

### fatture_routes copy.py

**Numero di route**: 2

| Route |
|-------|
| `/api/fatturazione/genera_fattura` |
| `/gestione_fatture` |

### fatture_routes.py

**Numero di route**: 6

| Route |
|-------|
| `/api/fatturazione/genera_fattura` |
| `/api/fatturazione/genera_fatture_da_cdr` |
| `/api/fatturazione/lista_clienti` |
| `/api/fatturazione/ordini_cliente/<int:partner_id>` |
| `/gestione_fatture` |
| `/gestione_ordini` |

### listino_routes copy.py

**Numero di route**: 9

| Route |
|-------|
| `/` |
| `/api/apply-markup` |
| `/api/export-csv` |
| `/api/files/delete/<filename>` |
| `/api/files/list` |
| `/api/last-file` |
| `/api/save` |
| `/api/upload` |
| `/static/<path:filename>` |

### listino_routes.py

**Numero di route**: 9

| Route |
|-------|
| `/listino` |
| `/listino/api/apply-markup` |
| `/listino/api/files/delete/<filename>` |
| `/listino/api/files/list` |
| `/listino/api/last-file` |
| `/listino/api/save` |
| `/listino/api/upload` |
| `/listino/logger/export-csv` |
| `/listino/static/<path:filename>` |

### menu_routes.py

**Numero di route**: 3

| Route |
|-------|
| `/api/breadcrumb` |
| `/api/breadcrumb/<endpoint>` |
| `/api/menu/items` |

### odoo_routes.py

**Numero di route**: 22

| Route |
|-------|
| `/api/docs` |
| `/api/odoo/partners` |
| `/api/odoo/partners/<int:partner_id>` |
| `/api/odoo/partners/search` |
| `/api/odoo/partners/select` |
| `/api/odoo/partners/summary` |
| `/api/odoo/payment_terms` |
| `/api/odoo/payment_terms/select` |
| `/api/odoo/products/select` |
| `/api/subscriptions` |
| `/api/subscriptions/<int:subscription_id>` |
| `/api/subscriptions/limit/<int:limit>` |
| `/api/subscriptions/partner/<int:partner_id>` |
| `/api/subscriptions/partner/<int:partner_id>/limit/<int:limit>` |
| `/api/subscriptions/select` |
| `/api/subscriptions/select/<int:subscription_id>` |
| `/api/subscriptions/select/limit/<int:limit>` |
| `/api/subscriptions/select/partner/<int:partner_id>` |
| `/api/subscriptions/select/partner/<int:partner_id>/limit/<int:limit>` |
| `/api/subscriptions/summary` |
| `/odoo_invoices` |
| `/odoo_partners` |

## 🗂️ Tutti i Route Ordinati

**Totale route unici**: 99

| Route | Metodo Tipico |
|-------|---------------|
| `/` | GET |
| `/api/apply-markup` | GET |
| `/api/breadcrumb` | GET |
| `/api/breadcrumb/<endpoint>` | GET |
| `/api/categories` | GET |
| `/api/categories/<category_name>` | GET |
| `/api/categories/bulk-update-markup` | PUT |
| `/api/categories/conflicts` | GET |
| `/api/categories/export` | GET |
| `/api/categories/global-markup` | GET |
| `/api/categories/health` | GET |
| `/api/categories/import` | GET |
| `/api/categories/pricing-preview` | GET |
| `/api/categories/reset-defaults` | GET |
| `/api/categories/statistics` | GET |
| `/api/categories/test-classification` | GET |
| `/api/categories/validate` | GET |
| `/api/cdr/categories_summary` | GET |
| `/api/cdr/contract_type` | GET |
| `/api/cdr/contracts_config` | GET |
| `/api/cdr/extract_contracts` | GET |
| `/api/cdr/process_with_categories/<path:filename>` | GET |
| `/api/cdr/reports_with_categories` | GET |
| `/api/cdr/test_category_matching` | GET |
| `/api/cdr/update_contract` | PUT |
| `/api/contracts/datatable/ajax` | GET |
| `/api/contracts/datatable/serverside` | GET |
| `/api/contracts/datatable/summary` | GET |
| `/api/contracts/datatable/test` | GET |
| `/api/contracts/info` | GET |
| `/api/contracts/process` | GET |
| `/api/contracts/process/status` | GET |
| `/api/docs` | GET |
| `/api/export-csv` | GET |
| `/api/fatturazione/genera_fattura` | GET |
| `/api/fatturazione/genera_fatture_da_cdr` | GET |
| `/api/fatturazione/lista_clienti` | GET |
| `/api/fatturazione/ordini_cliente/<int:partner_id>` | GET |
| `/api/files/delete/<filename>` | DELETE |
| `/api/files/list` | GET |
| `/api/last-file` | GET |
| `/api/menu/items` | GET |
| `/api/odoo/partners` | GET |
| `/api/odoo/partners/<int:partner_id>` | GET |
| `/api/odoo/partners/search` | GET |
| `/api/odoo/partners/select` | GET |
| `/api/odoo/partners/summary` | GET |
| `/api/odoo/payment_terms` | GET |
| `/api/odoo/payment_terms/select` | GET |
| `/api/odoo/products/select` | GET |
| `/api/save` | GET |
| `/api/subscriptions` | GET |
| `/api/subscriptions/<int:subscription_id>` | GET |
| `/api/subscriptions/limit/<int:limit>` | GET |
| `/api/subscriptions/partner/<int:partner_id>` | GET |
| `/api/subscriptions/partner/<int:partner_id>/limit/<int:limit>` | GET |
| `/api/subscriptions/select` | GET |
| `/api/subscriptions/select/<int:subscription_id>` | GET |
| `/api/subscriptions/select/limit/<int:limit>` | GET |
| `/api/subscriptions/select/partner/<int:partner_id>` | GET |
| `/api/subscriptions/select/partner/<int:partner_id>/limit/<int:limit>` | GET |
| `/api/subscriptions/summary` | GET |
| `/api/upload` | GET |
| `/api/voip/calculate` | GET |
| `/api/voip/update_prices` | PUT |
| `/cdr_analytics/process_all` | GET |
| `/cdr_analytics/report_details/<path:filename>` | GET |
| `/cdr_categories_dashboard` | GET |
| `/cdr_categories_edit` | PUT |
| `/cdr_categories_new` | POST |
| `/cdr_dashboard` | GET |
| `/config` | GET |
| `/default_page` | GET |
| `/gestione_contratti` | GET |
| `/gestione_fatture` | GET |
| `/gestione_ordini` | GET |
| `/health` | GET |
| `/list_ftp_files` | GET |
| `/listino` | GET |
| `/listino/api/apply-markup` | GET |
| `/listino/api/files/delete/<filename>` | DELETE |
| `/listino/api/files/list` | GET |
| `/listino/api/last-file` | GET |
| `/listino/api/save` | GET |
| `/listino/api/upload` | GET |
| `/listino/logger/export-csv` | GET |
| `/listino/static/<path:filename>` | GET |
| `/logs` | GET |
| `/manual_run` | GET |
| `/odoo_invoices` | GET |
| `/odoo_partners` | GET |
| `/pattern_examples` | GET |
| `/quick_schedule/<schedule_type>` | GET |
| `/schedule_info` | GET |
| `/static/<path:filename>` | GET |
| `/status` | GET |
| `/status_page` | GET |
| `/test_ftp` | GET |
| `/test_pattern` | GET |

## 📈 Statistiche

### Route per Prefisso API

| Prefisso | Numero Route |
|----------|-------------|
| `/api/categories` | 13 |
| `/api/subscriptions` | 11 |
| `/api/cdr` | 8 |
| `/api/odoo` | 8 |
| `/api/contracts` | 7 |
| `/listino/api` | 6 |
| `/api/fatturazione` | 4 |
| `/api/breadcrumb` | 2 |
| `/api/files` | 2 |
| `/api/voip` | 2 |
| `/api/apply-markup` | 1 |
| `/api/docs` | 1 |
| `/api/export-csv` | 1 |
| `/api/last-file` | 1 |
| `/api/menu` | 1 |
| `/api/save` | 1 |
| `/api/upload` | 1 |
| `/cdr_analytics/process_all` | 1 |
| `/cdr_analytics/report_details` | 1 |
| `/listino/logger` | 1 |
| `/listino/static` | 1 |
| `/quick_schedule/<schedule_type>` | 1 |
| `/static/<path:filename>` | 1 |

---
*Documento generato automaticamente dallo script di estrazione route*
