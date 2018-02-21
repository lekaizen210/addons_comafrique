# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    department_id = fields.Many2one('hr.department', 'Departement')
    section_id = fields.Many2one('account.analytic.account', 'Axe analytique')
    section_child_id = fields.Many2one('account.analytic.account', 'Sous-axe analytique')
    type = fields.Selection([('normal', 'Normal'),
                             ('section', 'Axe')], 'Type', default = 'normal')


class AnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.multi
    @api.depends('account_id', 'move_id', 'ref')
    def _get_analytic_section(self):
        self.section_id = self.account_id.section_id.id
        self.section_child_id = self.account_id.section_child_id.id
        self.department_id = self.account_id.department_id.id

    section_id = fields.Many2one('account.analytic.account', 'Axe analytique', compute = _get_analytic_section, store=True)
    section_child_id = fields.Many2one('account.analytic.account', 'Sous-axe analytique', compute = _get_analytic_section, store=True)
    department_id = fields.Many2one('hr.department', 'Departement', compute = _get_analytic_section, store=True)