# -*- coding: utf-8 -*-
{
    'name': "Expression de besoin",

    'summary': """
        Expression de besoin d'achat""",

    'description': """
        Ce module permet de centraliser les expressions de besoin au sein d'un processus de validation    """,

    'author': "VEONE",
    'website': "http://www.veone.net",


    'category': 'Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','purchase','account','account_accountant','account_analytic_default',
                'account_budget', 'hr', 'stock', 'product','comafrique_groups', 'board', 'sales_team'],

    # always loaded
    'data': [
        #'security/rules.xml',
        'security/ir.model.access.csv',
        'workflow/wkl_request.xml',
        'data/sequence.xml',
        'data/template.xml',
        'data/template_margin.xml',
        'view/request_view.xml',
        'view/purchase_view.xml',
        'view/user_view.xml',
        'view/hr_view.xml',
        'view/stock_view.xml',
        'view/product_category_view.xml',
        'view/budget_view.xml',
        'view/account_view.xml',
        'view/analytic.xml',
        'report/request_report.xml',
        'report/request_budget.xml',
        'report/request_margin.xml',
        'report/purchase_order.xml',
        'view/margin_view.xml',
        'view/margin_update.xml',
        'view/supplier_select_view.xml',
        'view/req_group_view.xml',
        'view/request_board.xml',
        'view/margin_board.xml',
        'view/config_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}