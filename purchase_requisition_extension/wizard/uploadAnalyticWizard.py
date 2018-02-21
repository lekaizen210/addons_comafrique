#-*- encoding:utf-8 -*-

import base64
import StringIO
import csv
from odoo import api, fields, models, exceptions, _
import io
import xlrd
import os
import zipfile


class AccountAnalyticUpload(models.TransientModel):
    _name= "account.analytic.upload"
    _description= "Gestion des uploads de fichiers"

    def _get_default_parent(self):
        parent_id= self._context.get('active_id')
        print parent_id
        if parent_id :
            return parent_id
        else :
            return False


    account_parent_id= fields.Many2one('account.analytic.account', 'Compte parent', required=True, default=_get_default_parent, readonly=True)
    data_file = fields.Binary(string='Fichier à charger', required=True)
    type= fields.Selection([('sousaxe', 'Sous Axe'), ('compte_ana', 'Compte Analytique')], 'Type de contenu', required=True)
    filename = fields.Char()

    def get_tag(self, name_tag=None):
        atag_obj= self.env['account.analytic.tag']
        if name_tag is not None :
            tag= atag_obj.search([('name', '=', name_tag)])
            if tag :
                return tag.id
            else :
                return False

    def get_sous_axe(self, sousaxe=None):
        aaa_obj= self.env['account.analytic.account']
        if sousaxe is not None :
            analytic= aaa_obj.search([('section_id', '=', self.account_parent_id.id), ('name', '=', sousaxe),
                                      ('code', '=', self.account_parent_id.code)])
            if analytic :
                print analytic
                return analytic._ids[0]
            else :
                return False
        else :
            return False

    def uploadSousAxe(self, sheet, index):
        print sheet.ncols
        print sheet.nrows
        ana_obj= self.env['account.analytic.account']
        while index!= sheet.nrows:
            try :
                row = sheet.row_values(index)
                vals = {
                    'name': row[0],
                    'section_id': self.account_parent_id.id,
                    'tag_ids': [ self.get_tag(row[1])],
                    'type': row[2],
                    'code': self.account_parent_id.code
                }
                print vals
                id = ana_obj.create(vals)
                print id
                index+=1
            except :
                raise exceptions.Warning(_('Il est survenu une erreur lors de la création des sous-axes'))


    def uploadAccountAnalytic(self, sheet, index):
        print sheet.ncols
        print sheet.nrows
        ana_obj= self.env['account.analytic.account']
        while index != sheet.nrows:
            # try :
            row = sheet.row_values(index)
            vals = {
                'name': row[0],
                'section_id': self.account_parent_id.id,
                'tag_ids': [ self.get_tag(row[1])],
                'type': 'normal',
                'code': self.account_parent_id.code,
            }
            section_child=  self.get_sous_axe(row[3])
            if section_child :
                vals['section_child_id']= section_child
            print vals
            id = ana_obj.create(vals)
            print id
            index+=1
            # except :
            #     raise exceptions.Warning(_('Il est survenu une erreur lors de la création des sous-axes'))

    @api.multi
    def updateLoadFile(self):
        data_file = base64.b64decode(self.data_file)
        book = xlrd.open_workbook(file_contents=data_file)
        print book.nsheets

        sh = book.sheet_by_index(0)
        print sh.nrows

        print sh.ncols

        title =  sh.row_values(0)
        print title
        i = 1
        if self.type == 'sousaxe':
            self.uploadSousAxe(sheet=sh, index=i)
        else :
            self.uploadAccountAnalytic(sheet=sh, index=i)
        #
        #
        # # print sheet names
        # print book.sheet_names()

class CrossoveredBudgetUploadWizard(models.TransientModel):
    _name= 'crossovered.budget.upload.wizard'

    buget_id = False

    file_data= fields.Binary('Budget à uploader', required=True)
    line_ids= fields.One2many('crossovered.budget.upload.line', 'wizard_id', 'Lines')

    data = []

    def getBuget_id(self):
        budget_id= self._context.get('active_id')
        if budget_id :
            budget= self.env['crossovered.budget'].search([('id', '=', budget_id)])
            if budget :
                return budget
            return False
        return False

    def getAnalytiqueAccount(self,  code, name):
        aaa_obj= self.env['account.analytic.account']
        if code and name :
            analytic= aaa_obj.search([('code', '=', code), ('name', '=', name),('type', '=', 'normal')])
            if analytic :
                print analytic
                return analytic._ids[0]
        return False

    def getPostBudgetaire(self, name):
        pb_obj= self.env['account.budget.post']
        if name :
            post_budgetaire= pb_obj.search([('name', '=', name)])
            if post_budgetaire :
                return post_budgetaire.id
        return False

    def getDataFromSheet(self, sheet):
        cb_obj= self.env['crossovered.budget.lines']
        if sheet is not None :
            index= 1
            while index!= sheet.nrows:
                row = sheet.row_values(index)
                print row
                index+=1
                try :
                    analytic= self.getAnalytiqueAccount(sheet.name, row[0])
                    post_budgetaire_id= self.getPostBudgetaire(row[1])
                    budget= self.getBuget_id()
                    if analytic is False or post_budgetaire_id is False :
                        continue
                    vals = {
                        'analytic_account_id': analytic,
                        'general_budget_id': post_budgetaire_id,
                        'planned_amount': row[2],
                        'crossovered_budget_id': budget.id,
                        'date_from': budget.date_from,
                        'date_to': budget.date_to
                    }
                    cb_obj.create(vals)
                    print vals
                    print analytic
                except:
                    print 'ok'
                # try :
                #     row = sheet.row_values(index)
                #     analytic= self.getAnalytiqueAccount(sheet.name, row[0])
                #     index+=1
                # except :
                #     raise exceptions.Warning(_('Il est survenu une erreur lors de la création des sous-axes'))

        else :
            return False

    @api.onchange('file_data')
    def loadFile_data(self):
        try :
            lines = []
            data_file = base64.b64decode(self.file_data)
            book = xlrd.open_workbook(file_contents=data_file)
            sheet_names = book.sheet_names()
            if sheet_names :
                for i in range(len(sheet_names)) :
                    vals = {
                        'name': sheet_names[i],
                        'active': False,
                    }
                    lines+= [vals]
            self.line_ids = lines
        except :
            print ''

    @api.one
    def updateLoadFile(self):
        active_lines= self.line_ids.filtered(lambda l: l.active)
        print active_lines
        buget= self.getBuget_id()
        lines= []
        if active_lines :
            try :
                lines = []
                data_file = base64.b64decode(self.file_data)
                book = xlrd.open_workbook(file_contents=data_file)
                for line in active_lines :
                    print line.name
                    sheet = book.sheet_by_name(line.name)
                    print sheet.name
                    self.getDataFromSheet(sheet)
            except :
                print 'ok'

        print self.data







class CrossoveredBudgetUploadLineWizard(models.TransientModel):
    _name= 'crossovered.budget.upload.line'

    name= fields.Char('Onglet', required=True)
    active= fields.Boolean('Active')
    wizard_id= fields.Many2one('crossovered.budget.upload.wizard', 'Budget', required=False)

