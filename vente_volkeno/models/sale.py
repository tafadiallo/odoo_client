# -*- coding: utf-8 -*-
from odoo import models, fields, api , _
from odoo.exceptions import ValidationError
from datetime import date

class Order(models.Model):
    _inherit = "sale.order"
    