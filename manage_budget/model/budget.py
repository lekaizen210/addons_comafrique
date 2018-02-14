#-*- coding: utf-8 -*-

from odoo import models, fields, api


class ManageBudget(models.Model):
    _name = "manage.budget"

    budget = fields.Many2one('crossovered.budget', 'Budget')
    purchase_request_id = fields.Many2one('purchase.request')

    @api.multi
    def write(self, vals):
        print vals
        if self.budget:
            purchase_request_obj = self.env['purchase.request']
            purchase_request = purchase_request_obj.browse(vals.get('purchase_request_id'))
            print purchase_request
            for line in purchase_request:
                print line.date

    # @api.depends('budget')
    # def get_budget_line(self):
    #     self.write()
