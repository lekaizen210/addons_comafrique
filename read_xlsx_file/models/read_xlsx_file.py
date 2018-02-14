#-*- coding:utf-8 -*-

from odoo import models, fields, api
from xlrd import open_workbook
import base64
import io
from openpyxl import Workbook,load_workbook


class ReadXlsxFile(models.TransientModel):
    _name = "read.xlsx.file"
    # axe = fields.Boolean('Axe')
    # sous_axe = fields.Boolean('Sous axe')
    # compte = fields.Boolean('Compte')
    name = fields.Char()
    file = fields.Binary('Fichier à importer')
    line_ids = fields.One2many('read.xlsx.file.line','file_id','Ligne de fichier')

    @api.depends('file')
    def get_file(self):
        if self.file:
            xlsx_line = []
            workbook = open_workbook(file_contents = base64.decodestring(self.file))
            sheets = workbook.sheet_names()
            for sheet_name in sheets:
                sh = workbook.sheet_by_name(sheet_name)
                self.name = sh.name
                for row_num in range(sh.nrows):
                    raw_values = sh.row_values(row_num)
                    # for data in raw_values:
                    xlsx_dict = {
                        'nom':raw_values[0],
                        'prenom':raw_values[1],
                        'age':raw_values[2]
                    }
                    xlsx_line = [xlsx_dict]
                self.line_ids = xlsx_line


class ReadXlsxFileLine(models.TransientModel):
    _name = "read.xlsx.file.line"

    nom = fields.Char('Nom')
    prenom = fields.Char('Prenom')
    age = fields.Integer('Age')
    file_id = fields.Many2one('read.xlsx.file')
