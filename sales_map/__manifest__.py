{
    'name': 'Sales Map View',
    'version': '1.2',
    'summary': 'Sales Map View',
    'sequence': 10,
    'author': "JD DEVS",
    'depends': ['base', 'sale', 'web'],
    'data': [
        "views/views.xml"
    ],
    'assets': {
        'web.assets_backend': [
            "sales_map/static/src/js/sale_map.js",
            "sales_map/static/src/css/map.css",
        ],
        'web.assets_qweb': [
            "sales_map/static/src/xml/map.xml",
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/assets/screenshots/banner.png'],
}
