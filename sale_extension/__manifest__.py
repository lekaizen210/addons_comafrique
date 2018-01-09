# -*- coding: utf-8 -*-
{
    'name': "Extension des ventes",

    'summary': """
        Customisation du module de vente""",

    'description': """
        Ce module permet d'appliquer des règles de gestion et des processus spécifiques au module de gestion des vente :
        Rajout de champs, Customisation des rapports, Alertes, Workflow de validation, etc.
    """,

    'author': "VEONE",
    'website': "http://www.veone.net",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','comafrique_groups', 'sale', 'purchase_requisition_extension', 'hr'],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'security/rules.xml',
        'data/template.xml',
        'views/partner_view.xml',
        'views/sale_view.xml',
        'views/margin_view.xml',
        'views/request_view.xml',
        'views/sale_layout_view.xml',
        'report/sale_report_templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}