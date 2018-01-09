# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from urlparse import urljoin
import werkzeug

#Gestion de fiche de marge
class request_margin(models.Model):
    _name = 'purchase.request.margin'
    _description = 'Fiche de marge'
    _inherit = 'mail.thread'
    _rec_name = 'number'
    _order = "id desc"

    #Récupère les adresses mail des destinataire à notifier dans le champ fonction "mail_destination" à chaque étape de validation
    @api.one
    def _get_mail_destination(self):
        model_id = False
        followers = ''
        ir_model_data = self.env['ir.model.data']
        group_obj = self.env['res.groups']

        if self.state == 'draft' and self.department_id.manager_id and self.department_id.manager_id.user_id :
            followers = self.department_id.manager_id.user_id.login
        elif self.state == 'department' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_control')[1]
        elif self.state == 'controle' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_dr_operation')[1]
        elif self.state == 'operation_dir' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_direction')[1]
        elif self.state in ('direction', 'operation') :
            followers = self.user_id.login

        if self.state not in ('draft','direction') :
            group_id = group_obj.browse(model_id)
            for user in group_id.users :
                followers = '%s;%s' % (user.login, followers)

        self.mail_destination = followers

    #Récupère les adresses mail des destinataire à notifier en cas de retour pour révision dans le champ fonction "mail_return_destination" à chaque étape de validation
    @api.one
    def _get_return_mail_destination(self):
        model_id = False
        followers = ''
        ir_model_data = self.env['ir.model.data']
        group_obj = self.env['res.groups']

        if self.state == 'department' :
            followers = self.user_id.login
        elif self.state == 'controle' :
            followers = self.department_id.manager_id.user_id.login
        elif self.state in ('operation', 'operation_dir') :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_control')[1]
        elif self.state == 'direction' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_dr_operation')[1]

        if self.state not in ('department','controle') :
            group_id = group_obj.browse(model_id)
            for user in group_id.users :
                followers = '%s;%s' % (user.login, followers)

        self.mail_return_destination = followers

    @api.one
    def _get_url_direct_link(self):
        """
        	génère l'url pour accéder directement au document en cours à partir du mail de notification envoyé à un utilisateur
        """
        res = {}
        res['view_type'] = 'form'
        res['model']= 'purchase.request.margin'
        ir_menu_obj = self.env['ir.ui.menu']
        menu_ref_id = False
        try :
            menu_ref_id = self.env['ir.model.data'].get_object_reference('purchase_requisition_extension',  'request_margin_menu')
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

    #Fonction de calcul de totaux : Montant commande Client HT (amount_total_order), Montant de la marge (margin), pourcentage de la marge (margin_percent)
    @api.one
    @api.depends('line_ids', 'amount_untaxed')
    def _get_totals(self):
        self.amount_total = sum(line.subtotal for line in self.line_ids)

        # for line in self.line_ids :
        #     self.amount_tax += sum((sline.amount * line.price_unit * line.quantity)/100 for sline in line.tax_id)
        #
        self.amount_total_order = self.amount_untaxed
        self.margin = self.amount_total_order - self.amount_total
        try :
            self.margin_percent = (self.margin / self.amount_total_order) * 100
        except :
            self.margin_percent = 0

    #Récupère par défaut l'identifant de l'utilisateur connecté
    def default_user_id(self):
        return self._uid

    #Séquencement automatique de la fiche de marge, surchage à la création
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        if vals.get('number','Fiche de marge')=='Fiche de marge':
            vals['number'] = self.env['ir.sequence'].get('purchase.request.margin') or 'Fiche de marge'

        return models.Model.create(self, vals)
    

    #Contrôles à la modification de la fiche de marge (surchage de méthode native)
    @api.multi
    def write(self, vals):
        model_id = False
        update_users = []
        ir_model_data = self.env['ir.model.data']
        group_obj = self.env['res.groups']

        margin_id = self.env['purchase.request.margin.commitment'].search([['margin_id','=',self.id]])
        request_id = self.env['purchase.request'].search([['state','in',('department', 'controle', 'direction')],['margin_id','=',self.id]])
        model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_control')[1]

        group_id = group_obj.browse(model_id)
        for user in group_id.users :
            update_users.append(user.id)

        if self._uid not in update_users :
            if margin_id :
                raise  exceptions.ValidationError("Des coûts ont déjà été engagés à partir de cette fiche de marge, vous ne pouvez donc la modifier. Veuillez vous reférer au Contrôle pour toute modification.")

            if request_id :
                raise  exceptions.ValidationError("Une demande liée à cette fiche de marge est en cours de validation, veuillez la remettre en brouillon avant toute modification de la fiche de marge.")

        return super(request_margin, self).write(vals)

    #Contrôle de l'unité de la référence de commande sur une fiche de marge
    @api.constrains('order_ref')
    def _check_order_ref(self):
        if self.order_ref :
            margin_id = self.env['purchase.request.margin'].search([['order_ref','=',self.order_ref], ['name','!=',self.name]], limit=1)
            if margin_id :
                print margin_id.amount_untaxed
                if margin_id.amount_untaxed != self.amount_untaxed :
                    raise exceptions.ValidationError(u'Cette commande (%s) a déjà été référencée sur une fiche de marge avec un autre montant (%s), '
                                                     u'veuillez saisir le même montant sur la présente fiche de marge' % (self.order_ref, margin_id.amount_untaxed))

                if margin_id.date != self.date :
                    raise exceptions.ValidationError(u'Cette commande (%s) a déjà été référencée sur une fiche de marge avec une autre date (%s), '
                                                     u'veuillez saisir la même date sur la présente fiche de marge' % (self.order_ref, margin_id.date))

        return True

    #Récupération par défaut de l'employé et de son département à la création de la fiche de marge
    @api.model
    def default_get(self, fields_list):
        data = models.Model.default_get(self, fields_list)
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        if employee_id :
            data['employee_id'] = employee_id.id
            data['department_id'] = employee_id.department_id.id

        return data

    #Chargement automatique des comptes analytiques rattachés au departement du commercial sur la fiche de marge (au niveau de la grille de détails)
    @api.onchange('department_id')
    def onchange_department_id(self):
        margin_line = []

        if self.department_id :
            model_id = self.env['purchase.request.margin.modele'].search([['department_id','=',self.department_id.id]])
            #raise exceptions.ValidationError(model_id)
            if model_id :
                for line in model_id.line_ids :
                    modele = {
                        'name': line.category_id.name,
                        'section_id': line.section_id.id,
                        'sous_section_id': line.sous_section_id.id,
                        'analytic_account_id': line.analytic_account_id.id
                    }
                    margin_line += [modele]

                self.line_ids = margin_line

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

    #Récupération automatique du seuil de marge
    @api.one
    @api.depends('amount_untaxed')
    def _get_margin_limit(self):
        limit = 0
        margin_limit = self.env['purchase.request.margin.limit'].search([['apply','=',True]])

        if margin_limit :
            limit = margin_limit.margin

        self.margin_limit = limit

    #Comptage du nombre d'expression de besoin liées à une fiche de marge
    @api.one
    def _field_count(self):
        Request = self.env['purchase.request']
        request = Request.search_count([['margin_id','=',self.id]])
        self.nb_request = request

    create_date = fields.Datetime('Date de création')
    url_link = fields.Char("Lien", compute=_get_url_direct_link)
    nb_request = fields.Integer(compute = _field_count)
    margin_limit = fields.Float('Seuil de marge', compute = _get_margin_limit, store=True)
    partner_id = fields.Many2one('res.partner', 'Client', required=True, domain=[('customer','=',True)])
    number = fields.Char('Référence', default = 'Fiche de marge', copy=False)
    name = fields.Char('Référence interne', required=False)
    order_ref = fields.Char('Référence BC', required=False)
    proforma_ref = fields.Char('Référence proforma', required=False)
    user_id = fields.Many2one('res.users', 'Créé par', default = default_user_id)
    employee_id = fields.Many2one('hr.employee', 'Commercial(e)', required=True)
    department_id = fields.Many2one('hr.department', 'Département', required=True)
    date = fields.Date('Date de Commande', required=True)
    amount_untaxed = fields.Float('Montant BC (HT)', help='Montant du bon de commande client hors taxe')
    amount_total = fields.Float('Montant Achats HTVA', compute = _get_totals, store = True, track_visibility = 'onchange')
    amount_total_order = fields.Float('Total Ventes HTVA', compute = _get_totals, store = True, track_visibility = 'onchange')
    margin = fields.Float('Total Marge', compute = _get_totals, store = True, track_visibility = 'onchange')
    margin_percent = fields.Float('Marge (%)', compute = _get_totals, store = True, track_visibility = 'onchange')
    mail_destination = fields.Char('Adresses mails', compute = _get_mail_destination)
    mail_return_destination = fields.Char('Adresses mails retour', compute = _get_return_mail_destination)
    notify = fields.Boolean('Notifier', default = True)
    forcing = fields.Boolean('Forcer Val. Direction')
    control_comment= fields.Text('Commentaire du Contrôle de Gestion')
    line_ids = fields.One2many('purchase.request.margin.line', 'margin_id', 'Lignes de marge')
    state = fields.Selection([
        ('draft','Brouillon'),
        ('department','Département'),
        ('controle','Contrôle de gestion'),
        ('operation','Direction Opérations'),
        ('operation_dir','Direction Opérations'),
        ('direction','Direction Générale'),
        ('refus','Refusé'),
        ('done','Validé'),
         ],    'Etat', select=True, readonly=True, default = 'draft', track_visibility = 'onchange')

    _sql_constraints = [('name_unique', 'UNIQUE(name)', 'Cette référence interne a déjà été saisie')]

    #Méthode du workflow de validation, mise en brouillon
    @api.one
    def action_draft(self):
        self.state = 'draft'

    #Méthode du workflow de validation, soumission au Chef de Département
    @api.one
    def action_department(self):
        if self.state == 'draft' :
            self.send_mail('email_template_margin')
        else :
            self.send_mail('email_template_margin_return')
        self.state = 'department'

    #Méthode du workflow de validation, soumission au Contrôle de Gestion
    @api.one
    def action_control(self):
        if self.state == 'department' :
            self.send_mail('email_template_margin')
        else :
            self.send_mail('email_template_margin_return')
        self.state = 'controle'

    #Méthode du workflow de validation, soumission au Directeur des Opérations
    @api.one
    def action_dr_operation(self):
        if self.state == 'controle' :
            self.send_mail('email_template_margin')
        else :
            self.send_mail('email_template_margin_return')

        if self.forcing or self.margin_percent < self.margin_limit :
            self.state = 'operation_dir'
        else :
            self.state = 'operation'

    #Méthode du workflow de validation, soumission à la Direction Générale
    @api.one
    def action_direction(self):
        self.send_mail('email_template_margin')

        self.state = 'direction'

    #Méthode du workflow de validation, validation finale
    @api.one
    def action_done(self):
        self.send_mail('email_template_margin_valide')
        self.state = 'done'

    #Méthode du workflow de validation, refus
    @api.one
    def action_refus(self):
        self.send_mail('email_template_margin_refus')
        self.state = 'refus'

    #Méthode du workflow de validation, notification manuelle
    @api.one
    def action_notify(self):
        self.send_mail('email_template_margin')

        print 'notification envoyée'


#Détails de la fiche de marge
class margin_line(models.Model):
    _name = 'purchase.request.margin.line'
    _description = 'Ligne de marge'

    @api.one
    @api.depends('price_unit', 'quantity')
    def _get_subtotal(self):
        self.subtotal = self.price_unit * self.quantity

    @api.onchange('analytic_account_id')
    def onchange_analytic_account_id(self):
        self.sous_section_id = self.analytic_account_id.section_child_id.id

    @api.one
    @api.depends('order_ref', 'name')
    def _get_order_ref(self):
        self.order_ref = self.margin_id.order_ref

    order_ref = fields.Char('Référence BC', required=False, compute=_get_order_ref, store=True)
    supplier_id = fields.Many2one('res.partner', 'Fournisseur')
    product_id = fields.Many2one('product.product', 'Article')
    partner_id = fields.Many2one('res.partner', 'Fournisseur', domain=[('supplier','=',True)])
    name = fields.Char('Description', required=True)
    section_id = fields.Many2one('account.analytic.account', 'Axe', domain = [('type','=','section'),('section_id','=',False)])
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytique')
    quantity = fields.Float('Quantité')
    price_unit = fields.Float('Prix unitaire HT')
    subtotal = fields.Float('Sous-Total', compute = _get_subtotal, store = True)
    margin_id = fields.Many2one('purchase.request.margin', 'Marge')

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.name = self.product_id.name

#Coûts engagés de la fiche de marge
class margin_commitment(models.Model):
    _name = 'purchase.request.margin.commitment'
    _rec_name = 'analytic_account_id'

    @api.one
    def _get_process(self):
        self.process = self.request_id.process

    request_id = fields.Many2one('purchase.request', 'Expression de besoin')
    margin_id = fields.Many2one('purchase.request.margin', 'Fiche de marge')
    partner_id = fields.Many2one('res.partner', 'Fournisseur')
    description = fields.Char('Description')
    order_ref = fields.Char('Référence BC')
    amount = fields.Float('Montant')
    order_amount = fields.Float('Montant BC', help='Montant de la commande du client')
    order_date = fields.Date('Date de commande')
    section_id = fields.Many2one('account.analytic.account', 'Axe')
    section_child_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
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

#Détail des coûts engagés de la fiche de marge
class request_budget_line(models.Model):
    _name = 'purchase.request.commitment.line'
    _rec_name = 'analytic_account_id'

    section_id = fields.Many2one('account.analytic.account', 'Axe')
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Compte analytique')
    margin_id = fields.Many2one('purchase.request.margin', 'Coût', required=False)
    request_id = fields.Many2one('purchase.request', 'Demande', required=False)
    order_ref = fields.Char('Référence BC')
    request_margin_id = fields.Many2one('purchase.request.margin.commitment', 'Engagement', required=False)
    cout_prevu = fields.Float('Coût global')
    cout_consomme = fields.Float('Coût consommé')
    cout_engage = fields.Float('Coût engagé')
    cout_encours = fields.Float('Coût en cours de val.')
    demande_encours = fields.Float('Demande en cours')
    marge_restante = fields.Float('Marge restante')
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

#Surchage des expressions de besoins, contrôles et vérifications des côuts engagés
class request(models.Model):
    _inherit = 'purchase.request'

    @api.one
    @api.depends('commitment_line_ids', 'margin_id')
    def _get_margin_totals(self):

        self.cout_engage = sum(mline.cout_consomme for mline in self.commitment_line_ids) + sum(mline.cout_engage for mline in self.commitment_line_ids)
        self.cout_global = self.margin_id.amount_total
        self.marge_restrante = self.cout_global - self.cout_engage

    commitment_line_ids = fields.One2many('purchase.request.commitment.line', 'request_id', 'Lignes de coûts')
    marge_restante = fields.Float('Marge restante')
    cout_global = fields.Float('Coût global', compute = _get_margin_totals, store=True)
    cout_engage = fields.Float('Total Coût engagé', compute = _get_margin_totals, store=True)
    marge_restrante = fields.Float('Coût restant', compute = _get_margin_totals, store=True)

    # @api.onchange('margin_id', 'line_ids')
    # def onchange_margin_id(self):
    #
    #     r_lines = []
    #     if self.margin_id :
    #
    #         if self.state == 'draft' :
    #
    #             for line in self.margin_id.line_ids :
    #
    #                 req_line_ids = {
    #                     'product_id': line.product_id.id,
    #                     'name': line.name,
    #                     'partner_id': line.partner_id.id,
    #                     'section_id': line.section_id.id,
    #                     'sous_section_id': line.sous_section_id.id,
    #                     'analytic_account_id': line.analytic_account_id.id,
    #                     'price_unit': line.price_unit,
    #                     'quantity': line.quantity,
    #
    #                 }
    #                 r_lines += [req_line_ids]
    #
    #             self.line_ids = r_lines

    @api.one
    def get_rappel_cout(self):
        c_lines = []
        found = set([])
        keep = []

        self.commitment_line_ids.unlink()

        for line in self.line_ids :

            demande = self.env['purchase.request.line'].search([['analytic_account_id','=',line.analytic_account_id.id], ['request_id','=',self.id]])
            margin_line = self.env['purchase.request.margin.line'].search([['analytic_account_id','=',line.analytic_account_id.id], ['margin_id','=',self.margin_id.id], ['order_ref','=',self.margin_id.order_ref]])
            engagements = self.env['purchase.request.margin.commitment'].search([['analytic_account_id','=',line.analytic_account_id.id], ['order_ref','=',self.margin_id.order_ref], ['state','=','nconsomme']])
            request_line_ids = self.env['purchase.request.line'].search([['analytic_account_id','=',line.analytic_account_id.id], ['state','=','direction']])

            somme_engagement = 0
            for engagement in engagements :
                somme_engagement += engagement.amount

            somme_encours = 0
            for encours in request_line_ids :
                somme_encours += encours.subtotal

            marge_encours = 0
            for m_encours in margin_line :
                marge_encours += m_encours.subtotal

            #raise exceptions.ValidationError(margin_line)

            demande_encours = 0

            # Construction d'une liste de compte analytique des lignes de demande sans doublons
            if line.analytic_account_id.id not in found:
                found.add(line.analytic_account_id.id)
                keep.append(line.analytic_account_id.id)

                # Récupération du montant en cours de demande par compte analytiue
                for dmde in self.line_ids :
                    if line.analytic_account_id.id == dmde.analytic_account_id.id :
                        demande_encours += dmde.subtotal

                commitment_line_ids = {
                    'order_ref': self.margin_id.order_ref,
                    'order_date': self.margin_id.date,
                    'section_id' : line.section_id.id,
                    'sous_section_id': line.sous_section_id.id,
                    'budget_id': self.budget_id.id,
                    'analytic_account_id': line.analytic_account_id.id,
                    'cout_prevu': marge_encours,
                    'cout_engage': somme_engagement,
                    'cout_encours': somme_encours,
                    'demande_encours': demande_encours,
                    'marge_restante': marge_encours - somme_engagement,

                }
                c_lines += [commitment_line_ids]

        self.commitment_line_ids = c_lines


class request_margin_category(models.Model):
    _name = 'purchase.request.margin.category'
    _description = "Categorie de cout"

    name = fields.Char('Catégorie', required=True)


class request_margin_category(models.Model):
    _name = 'purchase.request.margin.modele'
    _description = "Modele de cout"
    _rec_name = 'department_id'

    department_id = fields.Many2one('hr.department', 'Département', required=True)
    create_date = fields.Datetime('Date de création', readonly=True)
    line_ids = fields.One2many('purchase.request.margin.modele.line', 'modele_id', 'Ligne de modèle')

    _sql_constraints = [('department_unique', 'UNIQUE(department_id)', "Vous ne pouvez créer qu'un modèle par département")]


class request_margin_category(models.Model):
    _name = 'purchase.request.margin.modele.line'
    _description = "Ligne de modele de cout"

    @api.onchange('analytic_account_id')
    def onchange_analytic_account_id(self):
        self.sous_section_id = self.analytic_account_id.section_child_id.id

    category_id = fields.Many2one('purchase.request.margin.category', 'Catégorie de coût')
    section_id = fields.Many2one('account.analytic.account', 'Axe', domain = [('type','=','section'),('section_id','=',False)])
    sous_section_id = fields.Many2one('account.analytic.account', 'Sous-Axe')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytique')
    modele_id = fields.Many2one('purchase.request.margin.modele', 'Modèle')


