# -*- coding: utf-8 -*-
"""
    gateway

    "Nereid Payment Gateway"

    :copyright: (c) 2011-2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from nereid import abort
from nereid import jsonify
from nereid.globals import request, current_app
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta

__all__ = [
    'PaymentGateway', 'DefaultCheckout', 'PaymentGatewayCountry',
    'WebSite', 'PaymentGatewayWebsite', 'PaymentGatewaySale',
]
__metaclass__ = PoolMeta


class PaymentGateway(ModelSQL, ModelView):
    "Payment Gateway"
    __name__ = "nereid.payment.gateway"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    active = fields.Boolean('Active')
    is_allowed_for_guest = fields.Boolean('Is Allowed for Guest ?')
    available_countries = fields.Many2Many(
        'nereid.payment.gateway-country.country', 'gateway', 'country',
        'Countries Available')
    model = fields.Many2One(
        'ir.model', "Model", required=True,
        domain=[('model', 'ilike', 'nereid.payment.%')]
    )
    websites = fields.Many2Many('nereid.payment.gateway-nereid.website',
        'gateway', 'website', 'Websites')
    sequence = fields.Integer('Sequence', required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(PaymentGateway, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def default_active():
        "Sets active to True by default"
        return True

    @staticmethod
    def default_is_allowed_for_guest():
        "Sets is allowed for guest to True by default"
        return True

    @staticmethod
    def default_sequence():
        return 100

    @classmethod
    def _get_available_gateways(cls, country):
        """Return the list of tuple of available payment methods
        based on the country

        :param country: ID or active record of the country
        """
        domain = [
            ('available_countries', '=', int(country)),
            ('websites', '=', request.nereid_website.id),
        ]
        if request.is_guest_user:
            domain.append(('is_allowed_for_guest', '=', True))

        return cls.search(domain)

    def get_image(self):
        """Return an image for the given gateway. The API by default looks for
        the `get_image` method in the model of the given gateway. If there is
        such a method, the value returned from calling that method with the
        browse record of the method as argument is taken.
        """
        GatewayModel = Pool().get(self.model.model)

        if hasattr(GatewayModel, 'get_image'):
            return GatewayModel().get_image()
        return None

    @classmethod
    def get_available_gateways(cls):
        """Return the JSONified list of payment gateways available

        This is a XHR only method

        If type is specified as address then an address lookup is done
        """
        Address = Pool().get('party.address')

        value = request.args.get('value', 0, type=int)
        if request.values.get('type') == 'address':
            # Address lookup only when logged in
            if request.is_guest_user:
                abort(403)

            # If not validated as user's address this could lead to
            # exploitation by ID
            if value not in [a.id for a in
                    request.nereid_user.party.addresses]:
                abort(403)

            address = Address(value)
            value = address.country.id

        rv = [{
            'id': g.id,
            'name': g.name,
            'image': g.get_image(),
        } for g in cls._get_available_gateways(value)]

        return jsonify(result=rv)

    @classmethod
    def process(cls, sale, payment_method_id):
        """Begins the payment processing.

        Returns a response object if a redirect to third party website is
        required, else processes the payment.

        :param sale: Browse Record of the Sale
        :param payment_method_id: ID of payment method
        """
        Sale = Pool().get('sale.sale')

        try_to_authorize = (
            request.nereid_website.payment_mode == 'auth_if_available'
        )

        payment_method = cls(payment_method_id)
        allowed_gateways = cls._get_available_gateways(
            sale.invoice_address.country
        )
        if payment_method not in allowed_gateways:
            current_app.logger.error("Payment method %s is not valid" %
                payment_method.name)
            abort(403)

        payment_method_obj = Pool().get(payment_method.model.model)
        Sale.write([sale], {'payment_method': payment_method.id})

        if try_to_authorize and hasattr(payment_method_obj, 'authorize'):
            return payment_method_obj.authorize(sale)
        else:
            return payment_method_obj.capture(sale)


class DefaultCheckout:
    "Default Checkout Functionality process payment addition"

    __name__ = 'nereid.checkout.default'

    @classmethod
    def __setup__(cls):
        super(DefaultCheckout, cls).__setup__()

    @classmethod
    def _process_payment(cls, sale, form):
        """Process the payment

        :param sale: Browse Record of Sale Order
        :param form: Instance of validated form
        """
        PaymentGateway = Pool().get("nereid.payment.gateway")
        return PaymentGateway.process(sale, form.payment_method.data)


class PaymentGatewayCountry(ModelSQL):
    "Nereid Payment Country"
    __name__ = 'nereid.payment.gateway-country.country'

    gateway = fields.Many2One(
        'nereid.payment.gateway', 'Gateway', ondelete='CASCADE',
        required=True, select=True
    )
    country = fields.Many2One(
        'country.country', 'Country', ondelete='CASCADE',
        required=True, select=True
    )


class WebSite:
    "Add allowed gateways and payment mode"
    __name__ = "nereid.website"

    allowed_gateways = fields.Many2Many(
        'nereid.payment.gateway-nereid.website', 'website', 'gateway',
        'Allowed Payment Gateways'
    )
    payment_mode = fields.Selection([
        ('auth_if_available', 'Authorize if available'),
        ('capture', 'Capture'),
    ], 'Payment Capture mode', required=True)

    @staticmethod
    def default_payment_mode():
        "Set payment mode to capture by default"
        return 'capture'


class PaymentGatewayWebsite(ModelSQL):
    'Nereid Payment Gateway Website'
    __name__ = 'nereid.payment.gateway-nereid.website'

    website = fields.Many2One(
        'nereid.website', 'Website', required=True, select=True
    )
    gateway = fields.Many2One(
        'nereid.payment.gateway', 'Gateway', required=True, select=True
    )


class PaymentGatewaySale:
    "Extending Sale to include payment method"
    __name__ = "sale.sale"

    payment_method = fields.Many2One(
        'nereid.payment.gateway', 'Payment Method'
    )
