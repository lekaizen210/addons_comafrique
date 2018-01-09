# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
import time
from datetime import datetime
from urlparse import urljoin
import werkzeug

class request_type(models.Model):
    _name = 'purchase.request.type' 
    _description = 'Type de demande'
    
    name = fields.Char("Type de demande", required = True)
    #account_id = fields.Many2one('account.account', 'Compte')
    #post_id = fields.Many2one('account.budget.post', 'Poste')

class request_type(models.Model):
    _name = 'purchase.request.nature'
    _description = 'Nature du besoin'

    name = fields.Char("Nature de la demande", required = True)
    process = fields.Selection([('depense','Frais généraux'),
                                 ('investissement','Autorisation d\'investissement'),
                                 ('revente','Achat pour revente'),
                                 ], 'Type de la demande', select=True, readonly=False)
    #type_id = fields.Many2one('purchase.request.type', 'Type de demande', required=True)


class requisition(models.Model):
    _name = 'purchase.request'
    _description = 'Expression de besoin'  
    _inherit = 'mail.thread'
    _order = "name desc"
        
        
    #Récupération d'information par défaut (à la création) : Employé, Département, Poste
    @api.model
    def default_get(self, fields_list):
        data = models.Model.default_get(self, fields_list)
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])

        if employee_id :
            data['employee_id'] = employee_id.id
            data['department_id'] = employee_id.department_id.id
            data['job_id'] = employee_id.job_id.id

        return data

    #Mise à jour du département et du poste à la selection d'un employé
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.department_id = self.employee_id.department_id.id
        self.job_id = self.employee_id.job_id.id

    #Contrôle à la suppression d'une expression de besoin
    @api.multi
    def unlink(self):
        for request in self :
            if request.state != 'draft' :
                raise exceptions.ValidationError(str("Vous ne pouvez pas supprimer ce ducument, veuillez le mettre d'abord en brouillon"))
        return super(requisition, self).unlink()
        
    #Calcul de totaux
    @api.one
    @api.depends('line_ids')
    def _get_totals(self):
        self.amount_untaxed = sum(line.subtotal for line in self.line_ids)
        
        for line in self.line_ids :
            self.amount_tax += sum((sline.amount * line.price_unit * line.quantity)/100 for sline in line.tax_id)
            
        self.amount_total = self.amount_tax + self.amount_untaxed

    #Récupère les informations sur le budget : Budget alloué (allocated_budget),Montant engagé (aconso), Montant consommé (conso)
    #Somme des engagements et des demandes en cours (conso_ytd),Budget restant (remaining_budget)
    @api.one
    @api.depends('analytic_account_ids', 'budget_id', 'line_ids')
    def _get_budget(self):

        if self.request_budget_line_ids :

            self.allocated_budget = sum(line.montant_prevu for line in self.request_budget_line_ids)

            self.aconso = sum(line.montant_engage for line in self.request_budget_line_ids)

            self.conso = sum(line.montant_consomme for line in self.request_budget_line_ids)

            self.conso_ytd = sum(line.montant_engage for line in self.request_budget_line_ids) + sum(line.montant_consomme for line in self.request_budget_line_ids) + sum(line.montant_encours for line in self.request_budget_line_ids)

            self.remaining_budget = self.allocated_budget - sum(line.montant_engage for line in self.request_budget_line_ids) - sum(line.montant_consomme for line in self.request_budget_line_ids)
            


    #Récupère les adresses mail des destinataire à notifier dans le champ fonction "mail_destination" à chaque étape de validation
    @api.one
    def _get_mail_destination(self):
        model_id = False
        followers = ''
        ir_model_data = self.env['ir.model.data']
        group_obj = self.env['res.groups']
        
        if self.state == 'draft' and self.department_id.manager_id and self.department_id.manager_id.user_id :
            followers = self.department_id.manager_id.user_id.login
        elif self.state == 'department' and self.process != 'formation' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_dr_operation')[1]
        elif self.state == 'rh' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_dr_operation')[1]
        elif self.state == 'department' and self.process == 'formation' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_rh')[1]
        elif self.state == 'operation' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_control')[1]
        elif self.state == 'controle' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_direction')[1]
        elif self.state == 'direction' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_administration')[1]
        elif self.state in ('administration', 'standby') :
            followers = self.employee_id.user_id.login

        if self.state not in ('draft','administration') :
            group_id = group_obj.browse(model_id)
            for user in group_id.users :
                followers = '%s;%s' % (user.login, followers)
            
        self.mail_destination = followers
            
    #Surchage à  la création du bo de livraison
    @api.one
    def action_create_picking(self):
        
        bon_livr_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']

        if not self.location_id :
            raise exceptions.ValidationError(_("Veuillez renseigner l'emplacement source dans l'onglet Entrepôt"))
        
        if not self.location_dest_id :
            raise exceptions.ValidationError(_("Veuillez renseigner l'emplacement de destination dans l'onglet Entrepôt"))
            
        reference = self.env['ir.sequence'].get('stock.picking.out')
        picking_type_id = self.env['stock.picking.type'].search([['code','=','outgoing']])
        livraison = {
                         'name': reference,
                         'origin': self.name,
                         'min_date':self.date,
                         'max_date':time.strftime('%Y-%m-%d %H:%M:%S'),
                         'partner_id': self.employee_id.address_home_id.id,
                         'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                         'date_done':time.strftime('%Y-%m-%d %H:%M:%S'),
                         'stock_journal_id':1,
                         'picking_type_id': picking_type_id.id,
                         'location_id': self.location_id.id,
                         'location_dest_id': self.location_dest_id.id,
                         'move_type':'one',
                         'state':'draft',
                         'request_id': self.id,
                         
                    }
        
        livr_id = bon_livr_obj.create(livraison)
        
        for req in self.line_ids :
            if req.available_qty >= req.quantity :
                move_line = {
                                'name': self.name,
                                'priority':'1',
                                'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                                'date_expected':time.strftime('%Y-%m-%d %H:%M:%S'),
                                'product_id':req.product_id.id,
                                'product_uom_qty':req.quantity,
                                'product_uom':self.env['product.uom'].search([['id','=',req.product_id.uom_id.id]]).id,
                                'product_uos':self.env['product.uom'].search([['id','=',req.product_id.uom_id.id]]).id,
                                'location_id': self.location_id.id,
                                'location_dest_id': self.location_dest_id.id,
                                'picking_id':livr_id.id,
                                'picking_type_id':picking_type_id.id,
                                'partner_id': self.employee_id.address_home_id.id,
                                'state':'draft',
                                'origin': self.name,
                             }
            #else :
            #    raise exceptions.ValidationError(_("Il n'y a pas de quantité suffisante pour effectuer une livraison, veuillez lancer une commande d'approvisionnement !"))
         
        move_obj.create(move_line).action_confirm()
        
        self.state = 'done'

    @api.one
    def _get_url_direct_link(self):
        """
        	génère l'url pour accéder directement au document en cours
        """
        res = {}
        res['view_type'] = 'form'
        res['model']= 'purchase.request'
        #base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        #base_url = 'http://192.168.100.1'
        ir_menu_obj = self.env['ir.ui.menu']
        menu_ref_id = False
        try :
            menu_ref_id = self.env['ir.model.data'].get_object_reference('purchase_requisition_extension',  'expression_besoin')
            adresse = self.env['purchase.request.remote.access'].search([['apply','=',True]])
            if adresse :
                base_url = adresse.complete
            else :
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')

            if menu_ref_id :
                menu = ir_menu_obj.search([('id', '=', menu_ref_id[1])])
                res['menu_id']= menu.id
                res['action']= menu.action.id
                res['id']= self.id
            lien = werkzeug.url_encode(res)
            url= urljoin(base_url, "/web/?#%s" % (lien))
            self.url_link = url
            print(url)
        except :

            self.url_link = '#'

    #Comptage des enregistrements liés à l'expression de besoin : Commande fournisseur (nb_purchase),Livraisons fournisseur (nb_picking)
    @api.one
    def _field_count(self):
        Purchase = self.env['purchase.order']
        purchase = Purchase.search_count([['request_id','=',self.id]])
        self.nb_purchase = purchase

        Picking = self.env['stock.picking']
        picking = Picking.search_count([['request_id','=',self.id]])
        self.nb_picking = picking

    #Vérifie la disponibilité du stock
    @api.one
    @api.depends('line_ids')
    def _get_stock_dispo(self):
        trouve = False
        for line in self.line_ids :
            if line.available_qty >= line.quantity :
                trouve = True
            else :
                trouve = False
                break

        if trouve :
            self.stock_dispo = True

    @api.one
    def check_available_qty(self):
        for line in self.line_ids :
            line.available_qty = line.product_id.qty_available

        self.check_dispo = True

    #Contrôle à la suppression d'une expression de besoin
    @api.multi
    def unlink(self):
        for request in self :
            if request.state != 'draft' :
                raise exceptions.ValidationError(str("Vous ne pouvez pas supprimer ce ducument, veuillez le mettre d'abord en brouillon"))
        return super(requisition, self).unlink()

    #Enregistrement des engagements
    @api.one
    def _create_budget_validate_line(self):
        for line in self.line_ids :
            self.env['purchase.request.budget'].create({
                                                    'request_id': self.id,
                                                    'analytic_account_id': line.analytic_account_id.id,
                                                    'budget_id': self.budget_id.id,
                                                    'amount': line.subtotal})

            # Mise à jour des montants engagés et des montants en cours de validation sur les autres demandes en instance de traitement
            budget_line_ids = self.env['purchase.request.budget.line'].search([['analytic_account_id','=', line.analytic_account_id.id], ['budget_id','=',self.budget_id.id]])
            for b_line in budget_line_ids :
                self._cr.execute('update purchase_request_budget_line set montant_engage = (select sum(amount) from purchase_request_budget where analytic_account_id=%s and state=%s) where state not in (%s,%s)', (line.analytic_account_id.id, 'nconsomme', 'administration', 'done',))


        return True

    #Enregistrement des coûts engagés
    @api.one
    def create_margin_validate_line(self):
        for line in self.line_ids :
            self.env['purchase.request.margin.commitment'].create({
                                                    'request_id': self.id,
                                                    'order_ref': self.margin_id.order_ref,
                                                    'partner_id': line.partner_id.id,
                                                    'analytic_account_id': line.analytic_account_id.id,
                                                    'section_id': line.section_id.id,
                                                    'section_child_id': line.sous_section_id.id,
                                                    'margin_id': self.margin_id.id,
                                                    'amount': line.subtotal,
                                                    })
            #Mise à jour des coûts engagés
            margin_line_ids = self.env['purchase.request.commitment.line'].search([['analytic_account_id','=', line.analytic_account_id.id], ['margin_id','=',self.margin_id.id]])
            for b_line in margin_line_ids :
                self._cr.execute('update purchase_request_commitment_line set montant_engage = (select sum(amount) from purchase_request_margin_commitment where analytic_account_id=%s and state=%s) where state not in (%s,%s)', (line.analytic_account_id.id, 'nconsomme', 'administration', 'done',))



    #Provisionnement des informations de budget pour appréciation à la selection du budget
    @api.onchange('budget_id', 'line_ids')
    def onchange_budget_id(self):
        b_lines = []
        found = set([])
        keep = []

        if self.budget_id :

            for line in self.line_ids :

                demande = self.env['purchase.request.line'].search([['analytic_account_id','=',line.analytic_account_id.id]])
                budget_line = self.env['crossovered.budget.lines'].search([['analytic_account_id','=',line.analytic_account_id.id], ['crossovered_budget_id','=',self.budget_id.id]])
                engagements = self.env['purchase.request.budget'].search([['analytic_account_id','=',line.analytic_account_id.id], ['budget_id','=',self.budget_id.id], ['state','=','nconsomme']])
                request_line_ids = self.env['purchase.request.line'].search([['analytic_account_id','=',line.analytic_account_id.id], ['state','=','direction']])

                somme_engagement = 0
                for engagement in engagements :
                    somme_engagement += engagement.amount

                somme_encours = 0
                for encours in request_line_ids :
                    somme_encours += encours.price_unit

                demande_encours = 0

                # Construction d'une liste de compte analytique des lignes de demande sans doublons
                if line.analytic_account_id.id not in found :
                    found.add(line.analytic_account_id.id)
                    keep.append(line.analytic_account_id.id)

                    # Récupération du montant en cours de demande par compte analytiue
                    for dmde in self.line_ids :
                        if line.analytic_account_id.id == dmde.analytic_account_id.id :
                            demande_encours += dmde.subtotal

                    budget_line_ids = {
                        'section_id' : line.section_id.id,
                        'sous_section_id': line.sous_section_id.id,
                        'budget_id': self.budget_id.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'montant_prevu': budget_line.planned_amount,
                        'montant_consomme': budget_line.practical_amount,
                        'montant_engage': somme_engagement,
                        'montant_encours': somme_encours,
                        'demande_encours': demande_encours,
                        'montant_restant': budget_line.planned_amount - budget_line.practical_amount - somme_engagement,

                    }
                    b_lines += [budget_line_ids]

        self.request_budget_line_ids = b_lines



    # @api.one
    # @api.depends('line_ids')
    # def _get_analytic_account_ids(self):
    #     analytic_account_ids = []
    #
    #     if self.line_ids :
    #         for line in self.line_ids :
    #             analytic_account_ids.append({'id':line.analytic_account_id.id})
    #
    #     self.analytic_account_ids = analytic_account_ids

    @api.one
    @api.depends('margin_id')
    def _get_order_ref(self):
        self.order_ref = self.margin_id.order_ref
        self.margin_cost = self.margin_id.amount_total
        self.margin_rate = self.margin_id.margin_percent
        self.partner_id = self.margin_id.partner_id.id

    #Récupération des processus pour un bon affichage sur le masque de mail
    @api.one
    @api.depends('process')
    def _get_process_view(self):
        if self.process == 'depense' :
            self.process_view = 'Frais généraux & Marketing'
        elif self.process == 'investissement' :
            self.process_view = "Autorisation d'investissement"
        elif self.process == 'revente' :
            self.process_view = "Achat pour revente"
        elif self.process == 'formation' :
            self.process_view = "Formation du personnel"
        elif self.process == 'appro' :
            self.process_view = "Approvisionnement de stock"
        elif self.process == 'tiers' :
            self.process_view = "Achat pour compte de tiers"

    @api.one
    @api.depends('order_ref')
    def _get_order_id(self):
        order_id = self.env['purchase.order'].search([['name','=',self.order_ref]])
        if order_id :
            self.order_id = order_id.id

    name = fields.Char('Référence', size=128, required=True, default = 'Expression de besoin', copy=False)
    order_ref = fields.Char('Référence BC', size=128, copy=False, help='Référence de la commande client', compute = _get_order_ref, store=True)
    date = fields.Date('Date de demande', help='Date', required=True, states={'done':[('readonly',True)]})
    deadline = fields.Date("Echéance souhaitée", required=True, states={'done':[('readonly',True)]})
    url_link = fields.Char("Lien", compute=_get_url_direct_link)
    employee_id = fields.Many2one('hr.employee', 'Demandeur', required=True, readonly = False, help='Employé en charge de la demande selectionné automatiquement')
    order_id = fields.Many2one('purchase.order', 'Commande Frs', compute = _get_order_id, store=True)
    order_ref = fields.Char('Référence commande', copy=False)
    budget_id = fields.Many2one('crossovered.budget', 'Budget', copy=False)
    margin_id = fields.Many2one('purchase.request.margin', 'Réf. fiche de marge', copy=False)
    margin_cost = fields.Float('Coût global', store=True, compute = _get_order_ref)
    margin_rate = fields.Float('Taux de marge', store=True, compute = _get_order_ref)
    partner_id = fields.Many2one('res.partner', 'Client', required=False, compute = _get_order_ref, store =True)
    job_id = fields.Many2one('hr.job', 'Poste', readonly=False)
    department_id = fields.Many2one('hr.department', 'Département', readonly=False)
    nb_purchase = fields.Integer(compute = _field_count)
    nb_picking = fields.Integer(compute=_field_count)
    request_type = fields.Many2one('purchase.request.type', 'Type de l\investissement', required = False)
    request_nature = fields.Many2one('purchase.request.nature', 'Nature', required = False)
    amount_tax = fields.Float('Taxes', compute = _get_totals, store = True, track_visibility = 'onchange')
    amount_untaxed = fields.Float('Total hors-taxe', compute = _get_totals, store = True, track_visibility = 'onchange')
    amount_total = fields.Float('Montant Total', compute = _get_totals, store = True, track_visibility = 'onchange')
    justification = fields.Text('Justification', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Imputation analytique', required = False)
    analytic_account_ids = fields.One2many('purchase.request.budget.line', 'request_id', 'Imputation analytique', related='request_budget_line_ids')
    analytic_account_margin_ids = fields.One2many('purchase.request.commitment.line', 'request_id', 'Imputation analytique', related='commitment_line_ids')
    receive_date = fields.Date('Date reception', readonly = True, copy=False)
    allocated_budget = fields.Float('Budget global alloué', compute = _get_budget, store = True, copy=False)
    remaining_budget = fields.Float('Budget restant', compute = _get_budget, store = True, copy=False)
    conso = fields.Float('Budget consommé', compute = _get_budget, store = True, copy=False)
    aconso = fields.Float('Budget à consommer', help="Budget validé en attente de consommation", compute = _get_budget, store = True)
    conso_ytd = fields.Float('Conso YTD', compute = _get_budget, store = True)
    budget_note = fields.Text('Observation', copy=False)
    stock_dispo = fields.Boolean('Stock disponible', compute = _get_stock_dispo)
    budget_dispo = fields.Boolean('Budget', compute = _get_stock_dispo)
    check_dispo = fields.Boolean('Vérification dispo. stock', copy=False)
    create_uid = fields.Many2one('res.users', 'Créé par',states={'done':[('readonly',True)]})
    budget_responsible = fields.Many2one('res.users', 'Responsable du budget', readonly = True, copy=False)
    department_responsible = fields.Many2one('res.users', 'Chef de département', readonly = True, copy=False)
    operation_responsible = fields.Many2one('res.users', 'Direction des Opérations', readonly = True, copy=False)
    rh_responsible = fields.Many2one('res.users', 'Ressources Humaines', readonly = True, copy=False)
    direction_responsible = fields.Many2one('res.users', 'Direction', readonly = True, copy=False)
    department_date = fields.Date('Date de validation', help='Date', required=False, readonly = True, copy=False)
    operation_date = fields.Date('Date de validation', help='Date', required=False, readonly = True, copy=False)
    rh_date = fields.Date('Date de validation', help='Date', required=False, readonly = True, copy=False)
    control_date = fields.Date('Date de validation', help='Date', required=False, readonly = True, copy=False)
    direction_date = fields.Date('Date de validation', help='Date', required=False, readonly = True, copy=False)
    line_ids = fields.One2many('purchase.request.line', 'request_id', 'Détails du besoin', copy=True)
    mail_destination = fields.Char('Adresse mails', compute = _get_mail_destination)
    location_id = fields.Many2one('stock.location', 'Emplacement source', domain=[('usage','=','internal')], copy=False)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement de destination', domain=[('usage','=','customer')], copy=False)
    request_budget_line_ids = fields.One2many('purchase.request.budget.line', 'request_id', 'Rappel du budget')
    notify = fields.Boolean('Notifier', default = True)
    control_comment= fields.Text('Commentaire du Contrôle de Gestion')
    decision = fields.Selection([('accord','Accord'),
                                 ('report','Report'),
                                 ('refus','Refus'),
                                 ], 'Décision', select=True, readonly=True, copy=False)
    process = fields.Selection([('depense','Frais généraux & Marketing'),
                                 ('investissement','Autorisation d\'investissement'),
                                 ('revente','Achat pour revente'),
                                 ('formation','Formation du personnel'),
                                 ('appro','Approvisionnement de stock'),
                                 ('tiers','Achat pour compte de tiers'),
                                 ], 'Type de la demande', select=True, readonly=False)
    process_view = fields.Char('Processus', compute = _get_process_view)
    state_dep_budget = fields.Selection([
        ('autorise','Autorisé'),
        ('nautorise','Non-Autorisé'),
         ],    'Dépassement Budget', select=True, readonly=True, default = 'nautorise', copy=False)
    state = fields.Selection([
        ('draft','Brouillon'),
        ('department','Département'),
        ('operation','Direction Opérations'),
        ('rh','Ressources Humaines'),
        ('controle','Contrôle de gestion'),
        ('direction','Direction Générale'),
        ('administration','Service Q & L'),
        ('refus','Refusé'),
        ('standby','Reporté'),
        ('done','Terminé'),
         ],    'Etat', select=True, readonly=True, default = 'draft', track_visibility = 'onchange')

    
    
    @api.one
    def button_dummy(self):
        return True

	# @api.one
	# def send_notification(self, email_id, context=None):
	# 	template_id = self.env['ir.model.data'].get_object_reference('export_cca',  email_id)
	# 	try :
	# 		mail_templ = self.env['mail.template'].browse(template_id[1])
	# 		result = mail_templ.send_mail(res_id=self.id, force_send=True)
	# 		return True
	# 	except:
	# 		return False

    #Fonction d'envoi de mail
    @api.one
    def send_mail(self, email_id, context=None):
        template_id = self.env['ir.model.data'].get_object_reference('purchase_requisition_extension',  email_id)
        try :
            if self.notify :
                mail_templ = self.env['mail.template'].browse(template_id[1])
                result = mail_templ.send_mail(res_id=self.id, force_send=True)
            return True
        except:
            return False

        # template_obj = self.pool['mail.template']
        # ir_model_data = self.env['ir.model.data']
        # template_id = ir_model_data.get_object_reference('purchase_requisition_extension', 'email_template_request')[1]
        # template_obj.send_mail(template_id = template_id,  res_id = self.id, force_send=True)
    
    #Méthode du workflow de validation, mise en brouillon
    @api.one
    @api.model
    def action_draft(self):

        if self.state in ('direction','administration') :
            if self.process in ('depense', 'investissement') :
                for line in self.line_ids :
                    self.env['purchase.request.budget'].search([['analytic_account_id','=',line.analytic_account_id.id], ['budget_id','=',self.budget_id.id], ['state','=','nconsomme'], ['request_id','=',self.id]]).unlink()
            else :
                for line in self.line_ids :
                    self.env['purchase.request.margin.commitment'].search([['analytic_account_id','=',line.analytic_account_id.id], ['margin_id','=',self.margin_id.id], ['request_id','=',self.id]]).unlink()

        self.state = 'draft'
        
    #Méthode du workflow de validation, soumission au Chef de Département
    @api.one
    def action_department(self):
        """if self.amount_total > self.remaining_budget :
            raise exceptions.ValidationError(_("Il n'y pas assez de provision sur la ligne budgétaire de votre demande"))"""

        # if self.employee_id.user_id.id != self._uid :
        #     raise exceptions.ValidationError(_("Cette action ne peut être effectuée que par l'initiateur de la demande"))
        
        self._get_mail_destination()
        self.send_mail('email_template_request')
        self.state = 'department'
        
        
    #Méthode du workflow de validation, soumission au RH dans la cas d'une formation de personnel
    @api.one
    def action_rh(self):
        self.department_responsible = self.env.uid
        self.department_date = datetime.today()
        self.send_mail('email_template_request')
        self.state = 'rh'

    #Méthode du workflow de validation, soumission au Directeur des Opérations
    @api.one
    def action_dr_operation(self):
        if self.state == 'department' :
            self.department_responsible = self.env.uid
            self.department_date = datetime.today()
        elif self.state == 'rh' :
            self.rh_responsible = self.env.uid
            self.rh_date = datetime.today()
        self.send_mail('email_template_request')
        self.state = 'operation'

    #Méthode du workflow de validation, soumission au Contrôle de Gestion
    @api.one
    def action_control(self):
        self.operation_responsible = self.env.uid
        self.operation_date = datetime.today()
        self.receive_date = datetime.today()
        self.send_mail('email_template_request')
        self.state = 'controle'
        
    #Méthode du workflow de validation, soumission à la Direction Générale
    @api.one
    def action_direction(self):
        if not self.check_dispo :
            self.check_available_qty()

        if not self.commitment_line_ids and self.process == 'revente' :
            raise exceptions.ValidationError("Veuillez rappeler les côuts de la fiche de marge au niveau de l'onglet << COÛT >>. "
                                             "Assurez-vous d'être en mode édition (action sur le bouton << Modifier >>), puis cliquez sur le lien << Rappeler les coûts engagés >> au-dessus de la grille.")

        self.budget_responsible = self.env.uid
        self.control_date = time.strftime('%Y-%m-%d')
        self.send_mail('email_template_request')
        self.state = 'direction'
        
    #Méthode du workflow de validation,finalisation du processus de l'expression de besoin, génération automatique d'une éventuelle commande fournisseur
    @api.one
    def action_administration(self):
        self.direction_responsible = self.env.uid
        self.direction_date = time.strftime('%Y-%m-%d')
        self.decision = 'accord'

        if self.process in ('depense', 'investissement', 'formation') :
            self._create_budget_validate_line()
        elif  self.process == 'revente' :
            self.create_margin_validate_line()

        self.send_mail('email_template_request')
        self.state = 'administration'
        
    #Méthode du workflow de validation, Refus
    @api.one
    def action_refus(self):
        self.send_mail('email_template_request_refus')
        self.decision = 'refus'
        self.state = 'refus'
        
    #Génération automatique de commande fournisseur
    @api.one
    def action_do_order(self, request_id, rline_ids) :

        #raise exceptions.ValidationError('Bonjour')

        for line in rline_ids :
            if not line.partner_id :
                raise exceptions.ValidationError(_("Veuillez sélectionner un fournisseur !"))

        obj_purchase_order = self.env['purchase.order']
        obj_purchase_order_line = self.env['purchase.order.line']
        purchase_request = self.env['purchase.request']

        self.env.cr.execute("""SELECT dp.name,sum(quantity),p.id,price_unit,dp.partner_id,product_id,dp.analytic_account_id,dp.id
        FROM purchase_request p,purchase_request_line dp
        WHERE p.id=dp.request_id
        AND p.id = %s
        GROUP BY dp.name,p.id,price_unit,dp.partner_id,product_id,dp.analytic_account_id,dp.id""",(self.id,))

        line_ids = self.env.cr.fetchall()

        four = {}

        #Fonction de suppression de doublon
        def unique():
            found = set([])
            keep = []

            for dmde_achat in rline_ids :
                if dmde_achat.partner_id.id not in found:
                    found.add(dmde_achat.partner_id.id)
                    keep.append(dmde_achat.partner_id.id)

            return keep

        four = unique()

        if four :
            for frs in  four:
                reference = self.env['ir.sequence'].get('purchase.order')
                order_data = {
                                       'name': reference,
                                       'date_order': time.strftime('%Y-%m-%d'),
                                       'state': 'draft',
                                       'partner_id': frs,
                                       'pricelist_id': 1,
                                       'location_id':1,
                                       'amount_tax': self.amount_tax,
                                       'invoice_method':'order',
                                       'request_id': self.id,
                                 }
                order_id = obj_purchase_order.create(order_data)

                tax_list = []
                tax_id = False

                for pdt in line_ids :

                    # Vérification de la présence d'article au niveau de chaque ligne de demande
                    if not pdt[5] :
                        raise exceptions.ValidationError("Veuillez renseigner un article pour chaque ligne au niveau des Détails de besoin. "
                                                         "Au-dessus du formulaire, cliquez sur <<Action>> puis sur l'option <<MAJ Fournisseurs / Articles>>. "
                                                         "Ensuite en cliquant dans chaque cellule vide d'article, choisissez l'article dans la liste déroulante. "
                                                         "Vous pouvez procéder à une recherche rapide en commençant à saisir la référence ou la désignation de l'article dans le champ.")

                    if pdt[2]== request_id and pdt[4] == frs:

                        req_line_ids = self.env['purchase.request.line'].search([['request_id','=',request_id], ['product_id','=',pdt[5]], ['id','=',pdt[7]]])

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

        purchase_request.search([['id','=',request_id]]).state = 'done'

    #Méthode du workflow de validation, finalisation
    @api.one
    def action_done(self):
        
        self.action_do_order(self.id, self.line_ids)
                        

            
        #self.state = 'done'
        
    #Méthode du workflow de validation, report
    @api.one
    def action_standby(self):
        self.send_mail('email_template_request_report')
        self.decision = 'report'
        self.state = 'standby'
        
    #Sequencement automatique des expression de besoin, à la création
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if vals.get('name','Expression de besoin')=='Expression de besoin':
            vals['name'] = self.env['ir.sequence'].get('purchase.request') or 'Expression de besoin'
        
        return models.Model.create(self, vals)
    
    

    def view_requisition_order(self, cr, uid, ids, context=None):
        ir_model_data = self.pool.get('ir.model.data')
        try :
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'purchase_order_form')[1]
        except ValueError:
            compose_form_id = False 
        
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'res_id' : ids,
            #'target': 'new',
            #'context': req_context,
        }
    

    
#Détails de l'expression de besoin

class requisition_line(models.Model):
    _name = 'purchase.request.line'
    _description = 'Ligne de besoin'
    
    @api.one
    @api.depends('price_unit', 'quantity')
    def _get_subtotal(self):
        self.subtotal = self.price_unit * self.quantity
        
    @api.one
    @api.depends('prof')
    def _get_proforma(self):
        prof = 'Non'
        if self.prof :
            self.proforma = 'Oui'
            
            
    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.description or self.product_id.name
        """self.available_qty = self.product_id.qty_available
        self.price_unit = self.product_id.standard_price"""

    def _get_product_domain(self):
        return self.request_id.request_type.id

    @api.onchange('analytic_account_id')
    def onchange_analytic_account_id(self):
        self.sous_section_id = self.analytic_account_id.section_child_id.id
    
    product_id = fields.Many2one('product.product','Article', default = _get_product_domain)
    name = fields.Char('Description', required=True)
    partner_id = fields.Many2one('res.partner', 'Fournisseur', domain=[('supplier','=',True)])
    section_id = fields.Many2one('account.analytic.account', 'Axe', domain = [('type','=','section'),('section_id','=',False)])
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytique')
    quantity = fields.Float('Quantité', default = 1)
    available_qty = fields.Float('Qté dispo')
    price_unit = fields.Float('Prix unitaire')
    tax_id = fields.Many2many('account.tax', domain=[('type_tax_use','=','purchase')])
    subtotal = fields.Float('Sous-total HT', compute = _get_subtotal, store = True)
    prof = fields.Boolean('Prof.')
    proforma = fields.Char(compute = _get_proforma)
    request_id = fields.Many2one('purchase.request', 'Besoin')
    state = fields.Selection([
        ('draft','Brouillon'),
        ('department','Département'),
        ('controle','Contrôle de gestion'),
        ('direction','Direction Générale'),
        ('administration','Service Q & L'),
        ('refus','Refusé'),
        ('standby','Reporté'),
        ('done','Terminé'),
         ],    'Etat', select=True, default='draft', track_visibility = 'onchange', related='request_id.state')

#Engagements de l'expression de besoin

class request_validate_budget(models.Model):
    _name = 'purchase.request.budget'
    _description = 'Lignes de budget valides' 
    _rec_name = 'request_id' 

    @api.multi
    @api.depends('analytic_account_id', 'budget_id')
    def _get_analytic_section(self):
        self.section_id = self.analytic_account_id.section_id.id
        self.section_child_id = self.analytic_account_id.section_child_id.id
        self.department_id = self.analytic_account_id.department_id.id

    @api.one
    def _get_process(self):
        self.process = self.request_id.process

    section_id = fields.Many2one('account.analytic.account', 'Axe analytique', compute = _get_analytic_section, store=True)
    section_child_id = fields.Many2one('account.analytic.account', 'Sous-axe analytique', compute = _get_analytic_section, store=True)
    department_id = fields.Many2one('hr.department', 'Departement', compute = _get_analytic_section, store=True)
    create_date = fields.Datetime('Date de création')
    create_uid = fields.Many2one('res.users', 'Validé par')
    request_id = fields.Many2one('purchase.request', 'Demande', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    budget_id = fields.Many2one('crossovered.budget', 'Budget', required=True)
    amount = fields.Float('Montant validé')
    planned_amount = fields.Float('Montant prévu')
    invoice_id = fields.Many2one('account.invoice', 'Facture')
    state = fields.Selection([
        ('nconsomme','En attente de consommation'),
        ('consomme','Consommé'),
         ],    'Etat de consommation', select=True, readonly=True, default = 'nconsomme', track_visibility='onchange')
    process = fields.Selection([('depense','Frais généraux & Marketing'),
                                 ('investissement','Autorisation d\'investissement'),
                                 ('revente','Achat pour revente'),
                                 ('formation','Formation du personnel'),
                                 ('appro','Approvisionnement de stock'),
                                 ('tiers','Achat pour compte de tiers'),
                                 ], 'Type de la demande', select=True, readonly=False, compute = _get_process)


#Rappel des engagements sur le formulaire de l'expression de besoin

class request_budget_line(models.Model):
    _name = 'purchase.request.budget.line'
    _rec_name = 'analytic_account_id'


    section_id = fields.Many2one('account.analytic.account', 'Axe')
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    budget_id = fields.Many2one('crossovered.budget', 'Budget', required=False)
    request_id = fields.Many2one('purchase.request', 'Demande', required=False)
    request_budget_id = fields.Many2one('purchase.request.budget', 'Engagement', required=False)
    montant_prevu = fields.Float('Montant prévu')
    montant_consomme = fields.Float('Montant consommé')
    montant_engage = fields.Float('Montant engagé')
    montant_encours = fields.Float('En cours val. Direction')
    demande_encours = fields.Float('Demande en cours')
    montant_restant = fields.Float('Montant restant')
    color = fields.Integer('Couleur')
    state = fields.Selection([
        ('draft','Brouillon'),
        ('department','Département'),
        ('controle','Contrôle de gestion'),
        ('direction','Direction Générale'),
        ('administration','Admin. des ventes'),
        ('refus','Refusé'),
        ('standby','Reporté'),
        ('done','Terminé'),
         ],    'Etat', select=True, default='draft', track_visibility = 'onchange', related='request_id.state', store = True)

