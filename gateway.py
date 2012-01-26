# -*- coding: utf-8 -*-
"""
    gateway

    "Nereid Payment Gateway"

    :copyright: © 2011 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from nereid import abort
from nereid.helpers import jsonify
from nereid.globals import request, current_app
from trytond.model import ModelView, ModelSQL, ModelWorkflow, fields


class PaymentGateway(ModelSQL, ModelView):
    "Payment Gateway"
    _name = "nereid.payment.gateway"
    _description = __doc__

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    active = fields.Boolean('Active')
    is_allowed_for_guest = fields.Boolean('Is Allowed for Guest ?')
    available_countries = fields.Many2Many(
        'nereid.payment.gateway-country.country', 'gateway', 'country',
        'Countries Available')
    model = fields.Many2One('ir.model', "Model", required = True,
        domain = [('model', 'ilike', 'nereid.payment.%')])
    websites = fields.Many2Many('nereid.payment.gateway-nereid.website',
        'gateway', 'website', 'Websites')
    sequence = fields.Integer('Sequence', required=True, select=1)
    
    def __init__(self):	
        super(PaymentGateway, self).__init__()
        self._order.insert(0, ('sequence', 'ASC'))

    def default_active(self):
        "Sets active to True by default"
        return True

    def default_is_allowed_for_guest(self):
        "Sets is allowed for guest to True by default"
        return True
        
    def default_sequence(self):
        return 100

    def _get_available_gateways(self, bill_country_id):
        """Return the list of tuple of available payment methods
        """
        domain = [
            ('available_countries', '=', bill_country_id),
            ('websites', '=', request.nereid_website.id),
            ]
        if request.is_guest_user:
            domain.append(('is_allowed_for_guest', '=', True))

        return self.browse(self.search(domain))

    def get_image(self, gateway):
        """Return an image for the given gateway. The API by default looks for
        the `get_image` method in the model of the given gateway. If there is
        such a method, the value returned from calling that method with the
        browse record of the method as argument is taken. 
        """
        gateway_model_obj = self.pool.get(gateway.model.model)
        if hasattr(gateway_model_obj, 'get_image'):
            return gateway_model_obj.get_image(gateway)
        return None

    def get_available_gateways(self):
        """Return the JSONified list of payment gateways available

        This is a XHR only method

        If type is specified as address then an address lookup is done
        """
        address_obj = self.pool.get('party.address')

        value = int(request.args.get('value', 0))
        if request.values.get('type') == 'address':
            # Address lookup only when logged in
            if request.is_guest_user:
                abort(403)

            # If not validated as user's address this could lead to
            # exploitation by ID
            if value not in [a.id for a in
                    request.nereid_user.party.addresses]:
                abort(403)

            address = address_obj.browse(value)
            value = address.country.id

        rv = [{
            'id': g.id, 
            'name': g.name,
            'image': g.get_image(g),
                } for g in self._get_available_gateways(value)]
        return jsonify(result = rv)

    def process(self, sale, payment_method_id):
        """Begins the payment processing.

        Returns a response object if a redirect to third party website is
        required, else processes the payment.

        :param sale: Browse Record of the Sale
        :param payment_method_id: ID of payment method
        """
        sale_obj = self.pool.get('sale.sale')

        try_to_authorize = (
            request.nereid_website.payment_mode == 'auth_if_available')

        payment_method = self.browse(payment_method_id)
        allowed_gateways = self._get_available_gateways(
            sale.invoice_address.country.id)
        if payment_method not in allowed_gateways:
            current_app.logger.error("Payment method %s is not valid" % \
                payment_method.name)
            abort(403)

        payment_method_obj = self.pool.get(payment_method.model.model)
        sale_obj.write(sale.id, {'payment_method': payment_method.id})

        if try_to_authorize and hasattr(payment_method_obj, 'authorize'):
            return payment_method_obj.authorize(sale)
        else:
            return payment_method_obj.capture(sale)

PaymentGateway()


class DefaultCheckout(ModelSQL):
    "Default Checkout Functionality process payment addition"

    _name = 'nereid.checkout.default'
    
    def __init__(self):
        super(DefaultCheckout, self).__init__()

    def _process_payment(self, sale, form):
        """Process the payment

        :param sale: Browse Record of Sale Order
        :param form: Instance of validated form
        """
        payment_gateway_obj = self.pool.get("nereid.payment.gateway")
        return payment_gateway_obj.process(sale, form.payment_method.data)

DefaultCheckout()


class PaymentGatewayCountry(ModelSQL):
    "Nereid Payment Country"
    _name = 'nereid.payment.gateway-country.country'
    _description = __doc__

    gateway = fields.Many2One('nereid.payment.gateway', 'Gateway' ,
        ondelete='CASCADE', required=True, select=1)
    country = fields.Many2One('country.country', 'Country',
        ondelete='CASCADE', required=True, select=1)

PaymentGatewayCountry()


class WebSite(ModelSQL, ModelView):
    "Add allowed gateways and payment mode"
    _name = "nereid.website"

    allowed_gateways = fields.Many2Many(
        'nereid.payment.gateway-nereid.website', 'website', 'gateway',
        'Allowed Payment Gateways')
    payment_mode = fields.Selection([
        ('auth_if_available', 'Authorize if available'),
        ('capture', 'Capture'),
        ], 'Payment Capture mode', required=True)

    def default_payment_mode(self):
        "Set payment mode to capture by default"
        return 'capture'

WebSite()


class PaymentGatewayWebsite(ModelSQL):
    'Nereid Payment Gateway Website'
    _name = 'nereid.payment.gateway-nereid.website'
    _description = __doc__

    website = fields.Many2One('nereid.website', 'Website', required=True,
        select=1)
    gateway = fields.Many2One('nereid.payment.gateway', 'Gateway',
        required=True, select=1)

PaymentGatewayWebsite()


class PaymentGatewaySale(ModelWorkflow, ModelSQL, ModelView):
    "Extending Sale to include payment method"
    _name = "sale.sale"

    payment_method = fields.Many2One('nereid.payment.gateway', 
        'Payment Method')

PaymentGatewaySale()
