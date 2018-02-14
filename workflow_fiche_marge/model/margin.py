#-*- coding: utf-8 -*-

from odoo import models, fields, api


class Margin(models.Model):
    _inherit = 'purchase.request.margin'

    state = fields.Selection(selection_add=[('responsable', 'Responsable technique')])




