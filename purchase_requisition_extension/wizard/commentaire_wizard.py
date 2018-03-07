# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions

class RequestWizard(models.TransientModel):
    _name = 'commentaire.management.wizard'

    commentaire= fields.Text("Commentaire", required=True)

    @api.one
    def valide_commentaire(self):
        print self._context
        vals = {
            'res_model' : self._context.get('active_model'),
            'res_id': self._context.get('active_id'),
            'commentaire': self.commentaire
        }
        result = self.env['commentaire.managment'].create(vals)
        self.env[self._context.get('active_model')].browse(self._context.get('active_id')).action_draft()
        return result

