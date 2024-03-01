
from odoo import models, api,fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    project_client_tags = fields.Many2many('project.project', string='Project/Client')
    
    
    
    @api.model
    def create(self, vals):
        if vals.get('origin'):
            sale_order = self.env['sale.order'].search([('name', '=', vals.get('origin'))], limit=1)
            if sale_order:
                vals['partner_ref'] = sale_order.client_order_ref
                print(vals['partner_ref'])
        return super(PurchaseOrder, self).create(vals)
    
