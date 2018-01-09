# -*- coding: utf-8 -*-

from odoo import fields, models, api, exceptions
from datetime import datetime

class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account' 


class account_invoice(models.Model):
    _inherit = 'account.invoice' 
    
    #Récupérer la référence de l'expression de besoin sur la facture
    @api.one
    @api.depends('name','origin', 'number', 'reference')
    def _get_request_id(self):
        origin = self.origin
        purchase_id = self.env['purchase.order'].search([['name','=',origin]])
        if purchase_id :
            self.request_id = purchase_id.request_id.id
        

    @api.one
    def _get_autorisation_dep_budget(self):
        
        budget_valide = 0
        
        if self.request_id :
            budget_valide = self.request_id.amount_untaxed
        
        if self.amount_untaxed > budget_valide :
            self.autorise_dep_budget = True    
    
        
    #Fonction de contrôle avant imputation du budget : Compte comptable, poste budgétaire, montant facture par rapport au montant du besoin exprimé
    @api.multi
    def invoice_validate(self):
        res_id = super(account_invoice, self).invoice_validate()
        
        list_compte = []
        trouve = False
        
        for line in self.invoice_line_ids :
            
            if line.account_analytic_id :
                if line.account_analytic_id.crossovered_budget_line :
                    for budget_line in line.account_analytic_id.crossovered_budget_line :
                        for post_line in budget_line.general_budget_id.account_ids :
                            if post_line.code == line.account_id.code :
                                trouve = True
                            else :
                                list_compte.append(post_line.code)
                            
                if not trouve :
                    raise exceptions.ValidationError(u"Le compte <<%s>> ne figure pas dans les comptes paramétrés pour le poste budgétaire lié a ce compte analytique. Les comptes à choisir sont : %s" % (line.account_id.code, list_compte))
            
                if self.request_id and line.account_analytic_id.id != self.request_id.analytic_account_id.id :
                    raise exceptions.ValidationError(u"Le compte analytique sur les lignes de cette facture doit être le même que celui de l'expression de besoin %s" % self.request_id.name)
                
                budget_valide = self.request_id.amount_untaxed
                if self.request_id and self.amount_untaxed > budget_valide :
                    
                    if self.autorise_dep_budget and self.state_dep_budget_daf != 'autorise' :
                        raise exceptions.ValidationError(u"Le montant de la facture excède le budget autorisé (%s) pour l'expression de besoin liée à cette facutre (%s). Il faut une autorisation de dépassement de budget de la Direction Administrative et Financière" % (self.request_id.amount_untaxed, self.request_id.name))
                    
                    if self.autorise_dep_budget and self.state_dep_budget_daf == 'autorise' and self.state_dep_budget_direction != 'autorise':
                        raise exceptions.ValidationError(u"Le montant de la facture excède le budget autorisé (%s) pour l'expression de besoin liée à cette facutre (%s). Il faut une autorisation de dépassement de budget de la Direction Générale" % (self.request_id.amount_untaxed, self.request_id.name))
                    
                
                self.env['purchase.request.budget'].search([['request_id','=',self.request_id.id], ['analytic_account_id','=',line.account_analytic_id.id]]).write({'state': 'consomme', 'invoice_id': self.id})
                
                
        return res_id
    
    request_id = fields.Many2one('purchase.request', 'Expression de Besoin', compute = _get_request_id, store=True)
    autorise_dep_budget = fields.Boolean('Autorisation de dépassement', compute = _get_autorisation_dep_budget)
    dep_budget_validator_daf_id = fields.Many2one('res.users', 'Validateur')
    date_validation_daf = fields.Datetime('Date de validation')
    dep_budget_validator_dg_id = fields.Many2one('res.users', 'Validateur')
    date_validation_dg = fields.Datetime('Date de validation')
    state_dep_budget_direction = fields.Selection([
        ('autorise','Autorisé'),
        ('nautorise','Non-Autorisé'),
         ],    'Dépassement', select=True, readonly=True, default = 'nautorise', track_visibility='onchange')

        
    #Fonction d'autorisation de dépassement de budget
    @api.multi
    def action_depassement_budget_direction(self):
        self.dep_budget_validator_dg_id = self._uid
        self.date_validation_dg = datetime.today()
        
        self.state_dep_budget_direction = 'autorise'