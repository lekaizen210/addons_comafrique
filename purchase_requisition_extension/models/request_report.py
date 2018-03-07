# -*- coding: utf-8 -*-
from odoo import models, fields, tools

#Reporting des expressions de besoin, provisionning tableau de bord

class report_request(models.Model):
    _name='report.purchase.request'
    _description = 'Rapport des besoins'
    _auto = False


    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    budget_id = fields.Many2one('crossovered.budget', 'Budget')
    section_id = fields.Many2one('account.analytic.account', 'Section')
    section_child_id = fields.Many2one('account.analytic.account', 'Poste budgetaire')
    planned_amount = fields.Float('Montant prévu')
    validated_amount = fields.Float('Montant engagé')
    remain_amount = fields.Float('Montant restant')

    def init(self):

        tools.drop_view_if_exists(self.env.cr, 'report_purchase_request')
        self.env.cr.execute("""CREATE OR REPLACE VIEW report_purchase_request AS (
        select min(p.analytic_account_id) as id,
        p.analytic_account_id,
        budget_id,
        (select section_id from account_analytic_account where id=p.analytic_account_id),
        (select section_child_id from account_analytic_account where id=p.analytic_account_id),
        (select planned_amount from crossovered_budget_lines c where c.analytic_account_id=p.analytic_account_id) as planned_amount,
        sum(amount) as validated_amount,
        ((select planned_amount from crossovered_budget_lines c where c.analytic_account_id=p.analytic_account_id) - sum(amount)) as remain_amount
        from purchase_request_budget p, crossovered_budget_lines c
        where  p.analytic_account_id=c.analytic_account_id
        group by p.analytic_account_id, budget_id
                );
        """)

class report_margin(models.Model):
    _name='report.purchase.margin'
    _description = 'Rapport de marge par activite'
    _auto = False


    order_ref = fields.Char('Référence BC')
    section_id = fields.Many2one('account.analytic.account', 'Section')
    order_date = fields.Date('Date de commande')
    cout_global = fields.Float('Montant commande')
    cout_engage = fields.Float('Coût engagé')
    total_marge = fields.Float('Total marge')
    marge_pourcent = fields.Float('Marge (%)')

    def init(self):

        tools.drop_view_if_exists(self.env.cr, 'report_purchase_margin')
        self.env.cr.execute("""CREATE OR REPLACE VIEW report_purchase_margin AS (
        select
        distinct min(section_id) as id, order_ref, section_id, order_date
        from purchase_request_margin_commitment c
        group by order_ref, section_id,order_date
                );
        """)





