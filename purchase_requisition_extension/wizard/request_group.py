# -*- coding: utf-8 -*-

from openerp import models, fields, api, exceptions
import time
from datetime import datetime

class RequestWizard(models.TransientModel):
    _name = 'purchase.request.group.wizard'

    supplier_id = fields.Many2one('res.partner', 'Fournisseur')
    date = fields.Datetime('Date', default = datetime.today())
    request_ids = fields.Many2many('purchase.request', 'purchase_request_group_rel', 'request_id', 'group_id', 'Besoins')
    
    @api.one
    def action_group_request(self):

        request = self.env['purchase.request']
        for req in self.request_ids :
            #raise exceptions.ValidationError(req.line_ids)
            self.env['purchase.request'].search([['id','=',req.id]]).action_do_order(req.id, req.line_ids)

        return True

    @api.one
    def action_group_order(self):
        obj_purchase_order = self.env['purchase.order']
        obj_purchase_order_line = self.env['purchase.order.line']
        purchase_request = self.env['purchase.request']
        reference = self.env['ir.sequence'].get('purchase.order')
        req_list = []

        for req in self.request_ids :
            req_list.append(req.id)

        self.env.cr.execute("""SELECT dp.name,sum(quantity),p.id,price_unit,dp.partner_id,product_id,dp.analytic_account_id
        FROM purchase_request p,purchase_request_line dp
        WHERE p.id=dp.request_id
        AND p.id in %s
        GROUP BY dp.name,p.id,price_unit,dp.partner_id,product_id,dp.analytic_account_id""",(tuple(req_list),))

        line_ids = self.env.cr.fetchall()

        order_data = {
                       'name': reference,
                       'date_order': self.date,
                       'state': 'draft',
                       'partner_id': self.supplier_id.id,
                       'pricelist_id': 1,
                       'location_id':1,
                       #'amount_tax': self.amount_tax,
                       'invoice_method':'order',
                       #'request_id': self.id,
                     }
        order_id = obj_purchase_order.create(order_data)

        tax_list = []
        tax_id = False

        for pdt in line_ids :
            if pdt[2] in req_list and pdt[4] == self.supplier_id.id:

                req_line_ids = self.env['purchase.request.line'].search([['request_id','=',pdt[2]],['product_id','=',pdt[5]]])
                if req_line_ids.tax_id :
                    tax_id = req_line_ids.tax_id[0].id
                    tax_list.append(tax_id)

                product_id = self.env['product.product'].search([['id','=',pdt[5]]])

                line_data = {
                                'product_id': pdt[5],
                                'name': pdt[0],
                                'product_qty': pdt[1],
                                'product_uom': self.env['product.uom'].search([['id','=',product_id.uom_id.id]]).id,
                                'date_planned': time.strftime('%Y-%m-%d'),
                                'price_unit': pdt[3],
                                'taxes_id': [(6, 0, tax_list)],
                                'account_analytic_id': pdt[6],
                                'order_id': order_id.id
                            }

                purchase_id = obj_purchase_order_line.create(line_data)

        for r in req_list :
            purchase_request.search([['id','=',r]]).state = 'done'
            purchase_request.search([['id','=',r]]).order_ref = reference
            #self._cr.execute('update purchase_request set order_id=%s where id=%s',(r, purchase_id.id,))

        return order_id


    @api.onchange('supplier_id')
    @api.multi
    def onchange_supplier_id(self):
        req_list = []
        rlist = []

        request = self.env['purchase.request']
        #for req in self.request_ids :
        request_ids = request.search([['state','=','administration']])
        for r in request_ids :
            for l in r.line_ids :
                if self.supplier_id == l.partner_id :
                    req_list.append(r.id)

        srequest_ids = request.search([['id','in',req_list]])

        for req in srequest_ids :
            res = {
                'name': req.name,
                'employee_id': req.employee_id.id,
                'job_id': req.job_id.id,
                'department_id': req.department_id.id,
                'process': req.process,
                'date': req.date,
                'deadline': req.deadline,
                'amount_untaxed': req.amount_untaxed,
                'amount_total': req.amount_total,
                'state': req.state,
            }

            rlist += [res]

        # if self.supplier_id :
        #     self.request_ids = rlist
        #raise exceptions.ValidationError(srequest_ids)
            #req_list.append(req.id)

        #self.request_ids = req_list
    

    
    