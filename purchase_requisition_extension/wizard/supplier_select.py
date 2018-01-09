# -*- coding: utf-8 -*-

from openerp import models, fields, api, exceptions

class RequestWizard(models.TransientModel):
    _name = 'purchase.request.wizard'
    
    def _default_request(self):
        return self.env['purchase.request'].browse(self._context.get('active_id'))
    
    def _get_default_product(self):
        products = []
        request_id = self.env['purchase.request'].browse(self._context.get('active_id'))
        
        for wzd in request_id.line_ids :
            products.append({
                             'product_id': wzd.product_id.id,
                             'request_line_id': wzd.id,
                             'name': wzd.name,
                             'partner_id': wzd.partner_id.id,
                             #'wizard_id': self.id,
                             })
        #raise exceptions.ValidationError(products)
        return products
    
    
    def _get_defalut_state(self):
        return self.env['purchase.request'].browse(self._context.get('active_id')).state
    
    request_id = fields.Many2one('purchase.request',
        string="Expression de besoin", required=True, default = _default_request)
    request_state = fields.Char("Etat", default = _get_defalut_state)
    line_ids = fields.One2many('purchase.request.line.wzd','wizard_id', string="Lignes de besoin", default = _get_default_product)
    

    
    @api.multi
    def update_supplier(self):
        
        for line in self.line_ids :
            res = {'product_id':line.product_id.id,
                   'name': line.name,
                   'partner_id': line.partner_id.id}
            self.env['purchase.request.line'].search([['id','=',line.request_line_id.id]]).write(res)
            
            
        return {}
    
    
    
class purchase_request_line_wzd(models.TransientModel):
    _name = 'purchase.request.line.wzd'
    
    name = fields.Char('Description', required=True)
    product_id = fields.Many2one('product.product', 'Article', required=False)
    request_line_id = fields.Many2one('purchase.request.line', 'Ligne de demande', required=False)
    partner_id = fields.Many2one('res.partner', 'Fournisseur', domain=[('supplier','=',True)])
    wizard_id = fields.Many2one('purchase.request.wizard', 'Article')