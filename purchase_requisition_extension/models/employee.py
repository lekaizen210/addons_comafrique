# -*- coding: utf-8 -*-
from odoo import models, fields

#Rajout du numéro de la CNPS sur la fiche employé.
# Rattachement d'un ensemble du compte analytique à l'employé pour un provisionning automatique
#sur la fiche d'expressino de besoin. Cette fonctionnalité n'est pas utilisée, le contrôle de gestion choisi les compte appropriés une fois la demande à son niveau
class employee(models.Model):
    _inherit = 'hr.employee'

    cnps = fields.Char('Numéro CNPS')
    analytic_account_ids = fields.Many2many('account.analytic.account', 'employee_analytic_acccount_rel', 'employee_id',
                                           'analytic_account_id', 'Comptes analytiques autorisés')

#Rattachement d'un compte analytique au département.
class departmenent(models.Model):
    _inherit = 'hr.department'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Section', domain=[('type','=','section'),('section_id','=',False),('type','=','section')])