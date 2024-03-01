# -*- encoding: utf-8 -*-
#
from odoo import models ,api ,fields
from odoo.exceptions import UserError,ValidationError
from bs4 import BeautifulSoup
class AccountInvoice(models.Model):
      _inherit = "account.move"
      
      comm_prod_fact = fields.Text(string="Commentaire des Produits", compute="_compute_product_comments")
      
      
      @api.depends('invoice_line_ids')
      def _compute_product_comments(self):
            for order in self:
                  comments = []
                  if order.invoice_line_ids:
                        for line in order.invoice_line_ids:
                              product_comment = line.product_id.commentaire_produit if line.product_id.commentaire_produit else ''
                              comments.append(str(product_comment))
                        order.comm_prod_fact = '\n'.join(comments)
                  else:
                        order.comm_prod_fact = order.comm_prod_fact