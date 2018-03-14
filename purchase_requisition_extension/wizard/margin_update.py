# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

class RequestWizard(models.TransientModel):
    _name = 'purchase.request.margin.wizard'

    def _default_request(self):
        return self.env['purchase.request.margin'].browse(self._context.get('active_id'))

    def _get_default_product(self):
        lines = []
        margin_id = self.env['purchase.request.margin'].browse(self._context.get('active_id'))

        for wzd in margin_id.line_ids :
            lines.append({
                 'supplier_id': wzd.supplier_id.id,
                 'product_id': wzd.product_id.id,
                 'partner_id': wzd.partner_id.id,
                 'name': wzd.name,
                 'section_id': wzd.section_id.id,
                 'sous_section_id': wzd.sous_section_id.id,
                 'analytic_account_id': wzd.analytic_account_id.id,
                 'quantity': wzd.quantity,
                 'price_unit': wzd.price_unit,
                 'margin_line_id': wzd.id,

                 })

        return lines


    def _get_defalut_state(self):
        return self.env['purchase.request.margin'].browse(self._context.get('active_id')).state

    margin_id = fields.Many2one('purchase.request.margin',
        string="Fiche de marge", required=True, default = _default_request)
    request_state = fields.Char("Etat", default = _get_defalut_state)
    line_ids = fields.One2many('purchase.request.margin.line.wzd','wizard_id', string="Lignes de marge", default = _get_default_product)



    @api.multi
    def update_margin_lines(self):

        for line in self.line_ids :
            res = {
                 'supplier_id': line.supplier_id.id,
                 'product_id': line.product_id.id,
                 'partner_id': line.partner_id.id,
                 'name': line.name,
                 'section_id': line.section_id.id,
                 'sous_section_id': line.sous_section_id.id,
                 'analytic_account_id': line.analytic_account_id.id,
                 'quantity': line.quantity,
                 'price_unit': line.price_unit,

                 }
            self.env['purchase.request.margin.line'].search([['id','=',line.margin_line_id.id]]).write(res)
            self.margin_id._get_totals()


        return {}



class purchase_request_line_wzd(models.TransientModel):
    _name = 'purchase.request.margin.line.wzd'

    supplier_id = fields.Many2one('res.partner', 'Fournisseur')
    product_id = fields.Many2one('product.product', 'Article')
    partner_id = fields.Many2one('res.partner', 'Fournisseur', domain=[('supplier','=',True)])
    name = fields.Char('Description', required=True)
    section_id = fields.Many2one('account.analytic.account', 'Axe', domain = [('type','=','section'),('section_id','=',False)])
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytique')
    quantity = fields.Float('Quantité')
    price_unit = fields.Float('Prix unitaire HT')
    margin_id = fields.Many2one('purchase.request.margin', 'Marge')
    margin_line_id = fields.Many2one('purchase.request.margin.line', 'Ligne de marge', required=False)
    wizard_id = fields.Many2one('purchase.request.margin.wizard', 'Article')