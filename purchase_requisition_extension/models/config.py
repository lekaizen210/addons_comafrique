# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions

#Paramétrage de l'accès distant. Lorsque le bouton "apply" est coché, toute les alertes mails passent par l'adresse distante au lieu de l'adresse locale
class remote_access(models.Model) :
    _name = 'purchase.request.remote.access'
    _description = 'Acces distant'
    _rec_name = 'complete'

    @api.one
    @api.depends('protocole', 'adresse', 'port')
    def _get_name(self):
        self.complete = ('%s://%s:%s') % (self.protocole, self.adresse, self.port)

    complete = fields.Char('Adresse complète',compute = _get_name, store=True)
    protocole = fields.Selection([('http', 'http'),
                                  ('https','https')], 'Protocole', required=True)
    adresse = fields.Char('Adresse', required=True)
    port = fields.Integer('Port', default = '8069', size=4, required=True)
    apply = fields.Boolean('Appliquée par défaut')

    @api.constrains('apply')
    def _check_apply(self):
        nb = 0
        if self.apply :
            self._cr.execute('select count(*) from purchase_request_remote_access where apply = true')
            nb = self._cr.fetchone()[0]
            if int(nb) > 1 :
                raise exceptions.ValidationError('Il existe déjà une adresse appliquée par défaut')


#Limite de seuile de validation des fichier de marge. Au-delà du seuil, les fiches de marge doivent être validées par la Direction Générale (profil DG)
class remote_access(models.Model) :
    _name = 'purchase.request.margin.limit'
    _description = 'Seuil de marge'

    margin = fields.Float('Seuil de marge (%)')
    apply = fields.Boolean('Appliquée par défaut')

    @api.constrains('apply')
    def _check_apply(self):
        nb = 0
        if self.apply :
            self._cr.execute('select count(*) from purchase_request_margin_limit where apply = true')
            nb = self._cr.fetchone()[0]
            if int(nb) > 1 :
                raise exceptions.ValidationError('Il existe déjà un seuil de marge appliqué par défaut')

        if self.margin == 0 :
            raise exceptions.ValidationError('Veuillez renseigner une marge supérieure à 0')
