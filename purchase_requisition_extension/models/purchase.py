# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions
from urlparse import urljoin
import werkzeug

#Surchage des bons de commandes fournisseurs
class purchase(models.Model):
    _inherit = 'purchase.order'

    # @api.one
    # def _get_mail_destination(self):
    #     model_id = False
    #     followers = ''
    #     ir_model_data = self.env['ir.model.data']
    #     group_obj = self.env['res.groups']
    #
    #     if self.state in ('draft','sent') :
    #         model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_resp_adv')[1]
    #     elif self.state == 'submitted' :
    #         model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_direction')[1]
    #     elif self.state == 'purchase' :
    #         model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_administration')[1]
    #
    #     #if self.state not in ('draft','administration') :
    #     group_id = group_obj.browse(model_id)
    #     for user in group_id.users :
    #         followers = '%s;%s' % (user.login, followers)
    #
    #     self.mail_destination = followers

    @api.one
    def _get_url_direct_link(self):
        """
        	génère l'url pour accéder directement au document en cours
        """
        res = {}
        res['view_type'] = 'form'
        res['model']= 'purchase.order'
        #base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        #base_url = 'http://192.168.100.1'
        ir_menu_obj = self.env['ir.ui.menu']
        menu_ref_id = False
        try :
            menu_ref_id = self.env['ir.model.data'].get_object_reference('purchase',  'menu_purchase_form_action')
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

    @api.one
    def _get_order_lines(self):
        order_ids = []
        request_ids = self.env['purchase.request'].search([['order_ref','=',self.name]])

        for rq in request_ids :
            order_ids.append(rq.id)
            print 'bj'+str(rq.id)

    @api.one
    def _field_count(self):
        Request = self.env['purchase.request']
        request = Request.search_count([['order_id','=',self.id]])
        self.nb_request = request
    
    @api.one
    def _get_request_ref(self):
        if self.request_id :
            self.request_ref = self.request_id.name
        elif self.request_ids :
            temp = ''
            for r in self.request_ids :
                temp += r.name + ' | '

            self.request_ref = temp[0:len(temp)-2]

    #Récupère les adresses mail des destinataire à notifier dans le champ fonction "mail_destination" à chaque étape de validation
    @api.one
    def _get_mail_destination(self):
        model_id = False
        followers = ''
        ir_model_data = self.env['ir.model.data']
        group_obj = self.env['res.groups']

        if self.state in ('draft','sent') :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_resp_adv')[1]
        elif self.state == 'submitted' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_direction')[1]
        elif self.state == 'direction' :
            model_id = ir_model_data.get_object_reference('comafrique_groups', 'group_administration')[1]
        elif self.state == 'validated' :
            followers = self.create_uid.login

        if self.state not in ('validated') :
            group_id = group_obj.browse(model_id)
            for user in group_id.users :
                followers = '%s;%s' % (user.login, followers)

        self.mail_destination = followers


    request_id = fields.Many2one('purchase.request', 'Expression de besoin')
    request_ids = fields.One2many('purchase.request', 'order_id', 'Expressions de besoins')
    request_ref = fields.Char('Référence du besoin', compute = _get_request_ref)
    direction_user_id = fields.Many2one('res.users', 'Direction')
    url_link = fields.Char("Lien", compute=_get_url_direct_link)
    mail_destination = fields.Char('Adresse mails', compute = _get_mail_destination)
    nb_request = fields.Integer(compute = _field_count)
    notify = fields.Boolean('Notifier', default = True)
    state = fields.Selection([
        ('draft', 'Demande de prix'),
        ('sent', 'Demande de prix envoyée'),
        ('submitted', 'Responsable Q & L'),
        ('direction', 'Direction'),
        ('validated', 'Validé'),
        ('to approve', 'Commande à approuver'),
        ('purchase', 'Commande fournisseur'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé')
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')


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

    #Méthode du workflow de validation, soumission au Responsable Service Logistique & Qualité (SQL)
    @api.one
    def action_submit(self):
        self._get_mail_destination()
        self.send_mail('email_template_purchase_order')
        self.state = 'submitted'

    #Méthode du workflow de validation, soumission à la Direction Générale
    @api.one
    def action_direction(self):
        self._get_mail_destination()
        self.send_mail('email_template_purchase_order')
        self.state = 'direction'

    #Méthode du workflow de validation, validation de la Direction Générale
    @api.one
    def action_validate(self):
        self.direction_user_id = self._uid
        self._get_mail_destination()
        self.send_mail('email_template_purchase_order')
        self.state = 'validated'

    #Méthode du workflow de validation, confirmation du bon de commande par le Res. SQL ou son Assitant
    @api.one
    def action_confirm_order(self):
        self.state = 'sent'
        self.button_confirm()