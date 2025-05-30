MENU_ITEMS = [
    {
        'type': 'section',
      
    },
    {
        'endpoint': 'main.index',
        'title': 'Dashboard',
        'icon': 'ki-outline ki-element-11 fs-2',
    },
    {
        'type': 'section',  # Nessun titolo
        'title': 'Report'
    },
    {
        'title': 'Report',
        'icon': 'ki-outline ki-minus-folder fs-2',
        'children': [
            {
                'endpoint': 'main.report_mensile',
                'title': 'Report Mensili',
                'icon': 'ki-outline ki-element-11',
            },
            {
                'endpoint': 'main.report_annuale',
                'title': 'Report Annuali',
                'icon': 'ki-outline ki-setting-2 ',
            },
             {
                'endpoint': 'main.report_annuale',
                'title': 'Report Annuali',
            }
        ]
    },
    {
        'type': 'section',
        'title': 'Impostazioni'
    },
    {
        'endpoint': 'main.settings',
        'title': 'Impostazioni',
        'icon': 'ki-outline ki-setting-2 fs-2 ',
    }
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
