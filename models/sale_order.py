from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    portal_user_id = fields.Many2one('res.users', string='Portal User')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered')
    ], default='draft', string='Status')
