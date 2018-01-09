# -*- coding: utf-8 -*-

from odoo import fields, models

class SaleLayoutCategory(models.Model):
    _inherit = 'sale.layout_category'

    visible = fields.Boolean('Afficher les lignes', default = True)