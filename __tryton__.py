# -*- coding: UTF-8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

{
    'name': 'Nereid - Payment Gateway',
    'description': '''API to facilitate multiple payment gateways to integrate
        with nereid''',
    'version': '2.4.0.1dev',
    'author': 'Openlabs Technologies & Consulting (P) LTD',
    'email': 'info@openlabs.co.in',
    'website': 'http://www.openlabs.co.in/',
    'depends': [
        'nereid_checkout',
    ],
    'xml': [
        'gateway.xml',
        'defaults.xml',
        'urls.xml',
    ],
    'translation': [
    ],
}
