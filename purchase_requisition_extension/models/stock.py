# -*- coding: utf-8 -*-
from odoo import models, fields

class picking(models.Model):
    _inherit = 'stock.picking' 
    
    request_id = fields.Many2one('purchase.request', 'Expression de besoin')