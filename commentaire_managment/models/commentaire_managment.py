# -*- encoding:utf-8 -*-


from odoo import api, models, fields

class CommentaireManagment(models.Model):
    _name= 'commentaire.managment'
    _description= "Gestion des commnentaires"


    user_id= fields.Many2one('res.user', 'Utilisateur', required=True, default= lambda  r: r._uid)
    res_model= fields.Char('Modèle lié', required=True)
    res_id= fields.Integer('Id du model', required=True)
    commentaire= fields.Text('Commentaire', required=True)