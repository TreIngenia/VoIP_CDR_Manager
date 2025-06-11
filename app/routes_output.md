# 📋 Elenco Route Estratti

## 📊 Riepilogo

- **File analizzati**: 6
- **Route totali**: 79
- **Data estrazione**: 10/06/2025 21:20:45

## 📑 Indice dei File

- [cdr_categories_routes.py](#cdr_categories_routes-py) (16 route)
- [contratti_routes.py](#contratti_routes-py) (9 route)
- [default_routes.py](#default_routes-py) (24 route)
- [fatture_routes.py](#fatture_routes-py) (2 route)
- [menu_routes.py](#menu_routes-py) (3 route)
- [odoo_routes.py](#odoo_routes-py) (25 route)

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

**Numero di route**: 9

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

### fatture_routes.py

**Numero di route**: 2

| Route |
|-------|
| `/api/fatturazione/genera_fattura` |
| `/gestione_fatture` |

### menu_routes.py

**Numero di route**: 3

| Route |
|-------|
| `/api/breadcrumb` |
| `/api/breadcrumb/<endpoint>` |
| `/api/menu/items` |

### odoo_routes.py

**Numero di route**: 25

| Route |
|-------|
| `/api/odoo/company_info` |
| `/api/odoo/debug/compatibility_check` |
| `/api/odoo/debug/model_fields/<model_name>` |
| `/api/odoo/debug/test_data` |
| `/api/odoo/info` |
| `/api/odoo/invoices/<int:invoice_id>` |
| `/api/odoo/invoices/<int:invoice_id>/confirm` |
| `/api/odoo/invoices/bulk_create` |
| `/api/odoo/invoices/create` |
| `/api/odoo/partners` |
| `/api/odoo/partners/<int:partner_id>` |
| `/api/odoo/partners/search` |
| `/api/odoo/partners/select` |
| `/api/odoo/partners/summary` |
| `/api/odoo/payment_terms` |
| `/api/odoo/products` |
| `/api/odoo/quick_invoice` |
| `/api/odoo/services/available` |
| `/api/odoo/services/invoice/create` |
| `/api/odoo/services/invoice/quick` |
| `/api/odoo/services/invoice/validate` |
| `/api/odoo/test/create_sample_invoice` |
| `/api/odoo/test_connection` |
| `/odoo_invoices` |
| `/odoo_partners` |

## 🗂️ Tutti i Route Ordinati

**Totale route unici**: 78

| Route | Metodo Tipico |
|-------|---------------|
| `/` | GET |
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
| `/api/fatturazione/genera_fattura` | GET |
| `/api/menu/items` | GET |
| `/api/odoo/company_info` | GET |
| `/api/odoo/debug/compatibility_check` | GET |
| `/api/odoo/debug/model_fields/<model_name>` | DELETE |
| `/api/odoo/debug/test_data` | GET |
| `/api/odoo/info` | GET |
| `/api/odoo/invoices/<int:invoice_id>` | GET |
| `/api/odoo/invoices/<int:invoice_id>/confirm` | GET |
| `/api/odoo/invoices/bulk_create` | POST |
| `/api/odoo/invoices/create` | POST |
| `/api/odoo/partners` | GET |
| `/api/odoo/partners/<int:partner_id>` | GET |
| `/api/odoo/partners/search` | GET |
| `/api/odoo/partners/select` | GET |
| `/api/odoo/partners/summary` | GET |
| `/api/odoo/payment_terms` | GET |
| `/api/odoo/products` | GET |
| `/api/odoo/quick_invoice` | GET |
| `/api/odoo/services/available` | GET |
| `/api/odoo/services/invoice/create` | POST |
| `/api/odoo/services/invoice/quick` | GET |
| `/api/odoo/services/invoice/validate` | GET |
| `/api/odoo/test/create_sample_invoice` | POST |
| `/api/odoo/test_connection` | GET |
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
| `/health` | GET |
| `/list_ftp_files` | GET |
| `/logs` | GET |
| `/manual_run` | GET |
| `/odoo_invoices` | GET |
| `/odoo_partners` | GET |
| `/pattern_examples` | GET |
| `/quick_schedule/<schedule_type>` | GET |
| `/schedule_info` | GET |
| `/status` | GET |
| `/status_page` | GET |
| `/test_ftp` | GET |
| `/test_pattern` | GET |

## 📈 Statistiche

### Route per Prefisso API

| Prefisso | Numero Route |
|----------|-------------|
| `/api/odoo` | 23 |
| `/api/categories` | 13 |
| `/api/cdr` | 8 |
| `/api/contracts` | 4 |
| `/api/breadcrumb` | 2 |
| `/api/voip` | 2 |
| `/api/fatturazione` | 1 |
| `/api/menu` | 1 |
| `/cdr_analytics/process_all` | 1 |
| `/cdr_analytics/report_details` | 1 |
| `/quick_schedule/<schedule_type>` | 1 |

---
*Documento generato automaticamente dallo script di estrazione route*
