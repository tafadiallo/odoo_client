# -*- encoding: utf-8 -*-
from odoo import models ,api ,fields
import datetime


class ProductTemplate(models.Model):
    _inherit = "product.template"

    commentaire_produit = fields.Text(string = "Commentaire Produit")
