# -*- encoding: utf-8 -*-
from odoo import models ,api ,fields
import datetime


class ProductTemplate(models.Model):
    _inherit = "product.template"

    commentaire_produit = fields.Text(string = "Commentaire Produit")
    
    
    # @api.model
    # def create(self, vals):
    #     if 'default_code' not in vals or not vals['default_code']:
    #         vals['default_code'] = self._generate_default_code(vals.get('name'))

    #     return super(ProductTemplate, self).create(vals)

    # def _generate_default_code(self, name):
    #     existing_codes = self.env['product.template'].search([('default_code', 'like', default_code + '%')])
    #     if existing_codes:
    #         default_code += str(len(existing_codes) + 1)

    #     return default_code

