# sales_portal_backend/controllers/api.py
from odoo import http
from odoo.http import request, Response
import json


class SalesPortalAPI(http.Controller):

    # Fetch sales orders (GET)
    @http.route('/api/sales/orders', auth='user', methods=['GET'], type='json')
    def get_orders(self):
        user = request.env.user
        orders = request.env['sale.order'].sudo().search([('portal_user_id', '=', user.id)])
        return [{'id': order.id, 'name': order.name, 'status': order.status} for order in orders]

    # Create a new sale order (POST)
    @http.route('/api/sales/orders', type='http', auth='public', methods=['POST'], csrf=False)
    def create_order(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            customer = data.get('customerName', None)
            user = request.env.user  # Get logged-in portal user

            # Validate required fields
            if not customer or not data.get('order_lines'):
                return {"error": "Missing required fields"}, 400  # Return error with HTTP 400 status

            order_lines = []
            for line in data['order_lines']:
                product = request.env['product.product'].sudo().browse(line['product_id'])

                # Check if product exists
                if not product.exists():
                    return {"error": f"Product ID {line['product_id']} does not exist"}, 404

                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': line['quantity'],
                    'price_unit': product.lst_price,  # Use product price
                }))

            # Check if customer exists, else create
            customer_identifier = request.env['res.partner'].sudo().search([('name', '=', customer)], limit=1)
            if not customer_identifier:
                customer_identifier = request.env['res.partner'].sudo().create({
                    'name': customer,
                    'create_uid': user.id,
                    'customer_rank': 1,
                })

            # Create Sale Order
            order = request.env['sale.order'].sudo().create({
                'partner_id': customer_identifier.id,
                'state': 'sale',
                'user_id': user.id,
                'order_line': order_lines
            })
            # ✅ Automatically Create Invoice using Odoo's Method
            invoice = order._create_invoices()
            invoice.action_post()

            # Confirm Order (moves to 'sale' state)
            order.action_confirm()

            # Create Invoice
            invoice = request.env['account.move'].sudo().create({
                'move_type': 'out_invoice',
                'partner_id': customer_identifier.id,
                'invoice_origin': order.name,
                'invoice_line_ids': [(0, 0, {
                    'product_id': line[2]['product_id'],
                    'quantity': line[2]['product_uom_qty'],
                    'price_unit': line[2]['price_unit'],
                    'name': 'Invoice for Order ' + order.name
                }) for line in order_lines],
            })

            # Validate Invoice (Post it)
            invoice.action_post()

            return json.dumps({
                "message": "Order & Invoice created successfully",
                "order_id": order.id,
                "invoice_id": invoice.id
            })

        except Exception as e:
            return json.dumps({"error": str(e)})

