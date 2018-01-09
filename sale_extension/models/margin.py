# -*- coding: utf-8 -*-
from odoo import models, fields, api

class margin(models.Model):
    _inherit = 'purchase.request.margin'


    sale_id = fields.Many2one('sale.order', 'Devis Client')
    state = fields.Selection([
        ('draft','Brouillon'),
        ('department','Département'),
        ('controle','Contrôle de gestion'),
        ('operation','Direction Opérations'),
        ('operation_dir','Direction Opérations'),
        ('direction','Direction Générale'),
        ('refus','Refusé'),
        ('done','Validé'),
        ('closed','Terminé'),
         ],    'Etat', select=True, readonly=True, default = 'draft', track_visibility = 'onchange')

    @api.onchange('sale_id')
    def onchange_sale_id(self):
        self.partner_id = self.sale_id.partner_id
        self.amount_untaxed = self.sale_id.amount_untaxed
        self.date = self.sale_id.date_order

    @api.one
    def action_close(self):
        self.state = 'closed'

    @api.one
    def action_open(self):
        self.state = 'done'
