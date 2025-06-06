MENU_ITEMS = [
    {
        'type': 'section',
      
    },
    {
        'endpoint': 'index',
        'title': 'Dashboard',
        'icon': 'ki-outline ki-element-11 fs-2',
    },
    {
        'type': 'section',  # Nessun titolo
        'title': 'Report'
    },
    {
        'title': 'Gestione categorie',
        'icon': 'ki-outline ki-minus-folder fs-2',
        'children': [
            {
                'endpoint': 'cdr_categories_dashboard',
                'title': 'Dashboard categorie',
                'icon': 'ki-outline ki-element-11',
            },
            {
                'endpoint': 'cdr_categories_page',
                'title': 'Modifica categorie',
                'icon': 'ki-outline ki-notepad-edit ',
            },
             {
                'endpoint': 'cdr_categories_page_new',
                'title': 'Modifica categorie NEW',
                'icon': 'ki-outline ki-notepad-edit ',
            }
        ]
    },
    {
        'type': 'section',
        'title': 'Anagrafiche'
    },
    {
        'endpoint': 'gestione_utenti',
        'title': 'Gestione contratti',
        'icon': 'ki-outline ki-briefcase fs-2 ',
    },
    {
        'type': 'section',
        'title': 'Impostazioni sistema'
    },
    {
        'endpoint': 'config_page',
        'title': 'Impostazioni',
        'icon': 'ki-outline ki-setting-2 fs-2 ',
    },
    {
        'endpoint': 'logs',
        'title': 'Logs',
        'icon': 'ki-outline ki-devices fs-2 ',
    },
    {
        'endpoint': 'status_page',
        'title': 'Stato del sistema',
        'icon': 'ki-outline ki-pulse fs-2 ',
    },
]

# MENU_ITEMS = [
#     {
#         'endpoint': 'main.index',
#         'title': 'Dashboard',
#         'icon': 'ki-outline ki-element-11 fs-2',
#     },
#     {
#         'title': 'Report',
#         'icon': 'ki-outline ki-setting-2 fs-2',
#         'children': [
#             {
#                 'endpoint': 'main.report_mensile',
#                 'title': 'Report Mensili',
#             },
#             {
#                 'endpoint': 'main.report_annuale',
#                 'title': 'Report Annuali',
#             }
#         ]
#     },
#     {
#         'endpoint': 'main.settings',
#         'title': 'Impostazioni',
#         'icon': 'ki-outline ki-setting-2 fs-2 ',
#     }
# ]
