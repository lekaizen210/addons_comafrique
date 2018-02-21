# -*- coding: utf-8 -*-
from openerp import models, fields, api, exceptions
from datetime import datetime, timedelta
import time
from urlparse import urljoin
import werkzeug

class sale_order(models.Model):
    _inherit = 'sale.order'

    #Récupération du mail de destination
    @api.one
    def _get_mail_destination(self):
        model_id = False
        followers = ''
        followers_bpa = '%s;%s' % (self.user_id.login, self.department_id.manager_id.user_id.login)
        ir_model_data = self.env['ir.model.data']
        group_obj = self.env['res.groups']

        if self.state == 'draft' and self.department_id.manager_id and self.department_id.manager_id.user_id :
            followers = self.department_id.manager_id.user_id.login

        else :
            followers = self.user_id.login

        # Obtenir la liste des personnes à notifier pour les Bon Pour Accord
            control_users = ir_model_data.get_object_reference('comafrique_groups', 'group_control')[1]
            group_id = group_obj.browse(control_users)
            for user in group_id.users :
                followers_bpa = '%s;%s' % (user.login, followers_bpa)

            operations_users = ir_model_data.get_object_reference('comafrique_groups', 'group_dr_operation')[1]
            group_id = group_obj.browse(operations_users)
            for user in group_id.users :
                followers_bpa = '%s;%s' % (user.login, followers_bpa)

            sql_users = ir_model_data.get_object_reference('comafrique_groups', 'group_administration')[1]
            group_id = group_obj.browse(sql_users)
            for user in group_id.users :
                followers_bpa = '%s;%s' % (user.login, followers_bpa)

            sql_resp_users = ir_model_data.get_object_reference('comafrique_groups', 'group_resp_adv')[1]
            group_id = group_obj.browse(sql_resp_users)
            for user in group_id.users :
                followers_bpa = '%s;%s' % (user.login, followers_bpa)

        self.mail_destination = followers
        self.mail_destination_bpa = followers_bpa

    #Récupération de l'url du document
    @api.one
    def _get_url_direct_link(self):

        res = {}
        res['view_type'] = 'form'
        res['model']= 'sale.order'
        ir_menu_obj = self.env['ir.ui.menu']
        menu_ref_id = False
        try :
            menu_ref_id = self.env['ir.model.data'].get_object_reference('sale',  'menu_sale_quotations')
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

    #Affectation de valeurs par défaut
    @api.model
    def default_get(self, fields_list):
        data = models.Model.default_get(self, fields_list)
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        if employee_id :
            data['department_id'] = employee_id.department_id.id

        return data

    @api.one
    def send_mail(self, email_id, context=None):
        template_id = self.env['ir.model.data'].get_object_reference('sale_extension',  email_id)
        print 'Envoie de mail '
        try :
            if self.notify :
                mail_templ = self.env['mail.template'].browse(template_id[1])
                result = mail_templ.send_mail(res_id=self.id, force_send=True)
            return True
        except:
            return False

    @api.one
    def _field_count(self):
        Margin = self.env['purchase.request.margin']
        margin = Margin.search_count([['sale_id','=',self.id]])
        self.nb_margin = margin

    @api.one
    def _get_bpa_notif(self):
        #if date(self.date_relance_bpa) >= datetime.today().date() :
        self.notify_bpa = True
        #print str(self.date_relance_bpa.type)

    url_link = fields.Char("Lien", compute=_get_url_direct_link)
    department_id = fields.Many2one('hr.department', 'Département')
    contact_id = fields.Many2one('res.partner', 'Interlocuteur')
    mail_destination = fields.Char('Adresses mails', compute = _get_mail_destination)
    mail_destination_bpa = fields.Char('Adresses mails BPA', compute = _get_mail_destination)
    notify = fields.Boolean('Notifier', default = True)
    notify_bpa = fields.Boolean('Notifier BPA', compute = _get_bpa_notif)
    nb_margin = fields.Integer(compute = _field_count)
    margin_id = fields.Many2one('purchase.request.margin', 'Fiche de marge')
    date_relance_bpa = fields.Datetime('Relance BPA')
    order_object = fields.Char('Objet')
    picking_delay = fields.Char('Delai de livraison')
    purchase_delay = fields.Char("Delai d'approvisionnement")
    garantie = fields.Char('Garantie')
    state = fields.Selection([
        ('draft', 'Devis'),
        ('sent', 'Devis envoyé'),
        ('department', 'Département'),
        ('validated', 'Devis validé'),
        ('agreement', 'Bon Pour Accord'),
        ('sale', 'Commande'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    @api.one
    def action_department(self):
        self.send_mail('email_template_quotation')
        self.state = 'department'

    @api.one
    def action_validate(self):
        self.send_mail('email_template_quotation_validated')
        self.state = 'validated'

    @api.one
    def action_return(self):
        self.send_mail('email_template_quotation_return')
        self.state = 'draft'

    @api.one
    def action_agreement(self):
        start = fields.Datetime.from_string(self.date_order)
        duration = timedelta(hours=30*24, seconds=-1)
        self.date_relance_bpa = start + duration
        self.state = 'agreement'

    @api.one
    def create_purchase_request(self):
        request = {

        }

    # @api.constrains('layout_category_id')
    # def check_layout_category(self):


    #Cron pour alerte des bons pour accord datant d'une certaine durée
    @api.model
    def send_bpa_alert(self):
        d= datetime.now().date()
        d1 = datetime.strftime(d, '%Y-%m-%d %H:%M:%S')
        template_id = self.env['ir.model.data'].get_object_reference('sale_extension',  'email_template_bpa')
        order_list = []
        order_ids = self.env['sale.order'].search([['date_relance_bpa','<=',d1]])
        print order_ids

        for o in order_ids :

            try :
                mail_templ = self.env['mail.template'].browse(template_id[1])
                result = mail_templ.send_mail(res_id=o.id, force_send=True)
                print 'mail envoyé ' + str(o.id)

            except:
                return False

        print 'Notification de Bon Pour Accord ' + str(datetime.today())




class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    create_uid = fields.Many2one('res.users', 'Créé par')
    category_id = fields.Many2one('product.category', 'Famille')

    @api.onchange('category_id')
    def onchange_category_id(self):
        prod_list = []

        if self.category_id :
            product_ids = self.env['product.product'].search([['categ_id','=',self.category_id.id]])
        else :
            product_ids = self.env['product.product'].search([])

        for prod in product_ids :
            prod_list.append(prod.id)

        return {'domain': {'product_id': [('id','in',prod_list)]}}


    @api.model
    def write(self, vals):
        if self._uid != self.create_uid.id :
            raise exceptions.ValidationError("Veuillez vous référer à l'initiateur du devis pour la modification des lignes")

        return super(sale_order_line, self).write(vals)



