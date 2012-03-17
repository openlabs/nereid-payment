# -*- coding: utf-8 -*-
"""
    Default Payment Methods/Gateways

    COD(Cash on delivery) and Payment by Check/Money Order are 
        default payment methods/gateways

    :copyright: (c) 2010-2012 by Openlabs Technologies & Consulting (P) Ltd.
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelSQL


class COD(ModelSQL):
    "Cash on Delivery Payment Gateway"
    _name = 'nereid.payment.cod'
    _description = __doc__

    invoice_method = 'shipment'
    shipment_method = 'order'

    def capture(self, sale):
        """
        In COD payment is done by cash on delivery
        Hence setting invoice method in sale to postpaid
        """
        order_obj = self.pool.get('sale.sale')
        order_obj.write(sale.id, {
            'invoice_method': self.invoice_method,
            'shipment_method': self.shipment_method,
        })
        return True

COD()


class Cheque(ModelSQL):
    "Cheque/Money Order Payment Gateway"
    _name = 'nereid.payment.cheque'
    _description = __doc__

    invoice_method = 'order'
    shipment_method = 'invoice'

    def capture(self, sale):
        """
        Invoice method in sale to prepaid
        """
        order_obj = self.pool.get('sale.sale')
        order_obj.write(sale.id, {
            'invoice_method': self.invoice_method,
            'shipment_method': self.shipment_method,
        })
        return True

Cheque()
