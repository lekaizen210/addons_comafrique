# -*- coding: utf-8 -*-
from odoo import models, fields

class users(models.Model):
    _inherit = 'res.users' 
    
    digital_signature =  fields.Binary('Signature numérique')