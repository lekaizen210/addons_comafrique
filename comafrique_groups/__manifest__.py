# -*- coding: utf-8 -*-
{
    'name': "Profils COMAFRIQUE",

    'summary': """
        Profils COMAFRIQUE""",

    'description': """
        Gestion des habilitations des profils d'utilisateurs de COMAFRIQUE
    """,

    'author': "VEONE",
    'website': "http://www.veone.net",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Access right',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/groups.xml',

    ],
    # only loaded in demonstration mode
    'demo': [

    ],
}