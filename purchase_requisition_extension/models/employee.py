# -*- coding: utf-8 -*-
from odoo import models, fields

class employee(models.Model):
    _inherit = 'hr.employee'

    cnps = fields.Char('Numéro CNPS')
    analytic_account_ids = fields.Many2many('account.analytic.account', 'employee_analytic_acccount_rel', 'employee_id',
                                           'analytic_account_id', 'Comptes analytiques autorisés')

class departmenent(models.Model):
    _inherit = 'hr.department'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Section', domain=[('type','=','section'),('section_id','=',False),('type','=','section')])