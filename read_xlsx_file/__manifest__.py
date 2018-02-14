##############################################################################
# Copyright (c) 2018 Veone - http://www.veone.net
# Author: Team odoo (VEONE)
# ##############################################################################
{
    "name" : "Upload file",
    "version" : "1.0",
    "sequence":3,
    "author" : "Team odoo(VEONE)",
    'category': 'Finance',
    "website" : "http://www.veone.net",
    "depends" : ["base", "account", "account_budget"],
    "description": """
    """,
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml":[
        "views/read_xlsx_file.xml",
        ],
    "installable": True
}
