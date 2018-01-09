# -*- coding: utf-8 -*-
from odoo import models, fields

class product_category(models.Model):
    _inherit = 'product.category'

    code = fields.Char('Code')
    note = fields.Char('Note')