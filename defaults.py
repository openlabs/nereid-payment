# -*- coding: utf-8 -*-
"""
    Default Payment Methods/Gateways

    COD(Cash on delivery) and Payment by Check/Money Order are
        default payment methods/gateways

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.model import ModelSQL
from trytond.pool import Pool

__all__ = ['COD', 'Cheque']


class COD(ModelSQL):
    "Cash on Delivery Payment Gateway"
    __name__ = 'nereid.payment.cod'

    invoice_method = 'shipment'
    shipment_method = 'order'

    @classmethod
    def capture(cls, sale):
        """
        In COD payment is done by cash on delivery
        Hence setting invoice method in sale to postpaid
        """
        Sale = Pool().get('sale.sale')

        Sale.write([sale], {
            'invoice_method': cls.invoice_method,
            'shipment_method': cls.shipment_method,
        })
        return True


class Cheque(ModelSQL):
    "Cheque/Money Order Payment Gateway"
    __name__ = 'nereid.payment.cheque'

    invoice_method = 'order'
    shipment_method = 'invoice'

    def capture(cls, sale):
        """
        Invoice method in sale to prepaid
        """
        Sale = Pool().get('sale.sale')

        Sale.write([sale], {
            'invoice_method': cls.invoice_method,
            'shipment_method': cls.shipment_method,
        })
        return True
