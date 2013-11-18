# -*- coding: utf-8 -*-
'''

    Nereid Payment Gateway Test Suite

    :copyright: (c) 2010-2013 by Openlabs Technologies & Consulting (P) Ltd.
    :license: GPLv3, see LICENSE for more details
'''
import json
import unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, DB_NAME, CONTEXT
from trytond.transaction import Transaction

from trytond.modules.nereid_cart_b2c.tests.test_product import BaseTestCase


class TestPayment(BaseTestCase):
    """Test Payment Gateway"""

    def setUp(self):
        super(TestPayment, self).setUp()
        trytond.tests.test_tryton.install_module('nereid_payment')

        self.Address = POOL.get('party.address')
        self.Payment = POOL.get('nereid.payment.gateway')

        self.templates.update({
            'localhost/checkout.jinja': '{{form.errors|safe}}',
        })

    def test_0010_check_cart(self):
        """Assert nothing broke the cart."""
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('/cart')
                self.assertEqual(rv.status_code, 200)

                c.post('/cart/add', data={
                    'product': self.product1.id, 'quantity': 5
                })
                rv = c.get('/cart')
                self.assertEqual(rv.status_code, 200)

            sale, = self.Sale.search([])
            self.assertEqual(len(sale.lines), 1)
            self.assertEqual(sale.lines[0].product, self.product1)

    def test_0020_find_gateways(self):
        """
        Find the payment gateways when there are none
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                rv = c.get('/_available_gateways?value=777666554')
                self.assertEqual(json.loads(rv.data), {u'result': []})

    def test_0030_find_after_adding_country(self):
        """
        Add countries and then add to website
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            website, = self.NereidWebsite.search([])
            payment_method = self.Payment.search([])[0]
            self.Payment.write([payment_method], {
                'available_countries': [('add', map(int, website.countries))]
            })
            country_id = website.countries[0].id

            with app.test_client() as c:
                result = c.get(
                    '/_available_gateways?value=%s' % country_id
                )
                # False because its not added to website
                self.assertFalse(
                    payment_method.id in json.loads(result.data)['result']
                )

            self.NereidWebsite.write([website], {
                'allowed_gateways': [('add', [payment_method])]
            })

            with app.test_client() as c:
                result = c.get(
                    '/_available_gateways?value=%s' % country_id
                )
                json_result = json.loads(result.data)['result']
                self.assertEqual(len(json_result), 1)
                self.assertTrue(
                    payment_method.id in [t['id'] for t in json_result]
                )

    def test_0040_address_as_guest(self):
        """
        When address lookup is invoked as guest it should fail
        """
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            with app.test_client() as c:
                result = c.get(
                    '/_available_gateways?value=1&type=address'
                )
                self.assertEqual(result.status_code, 403)

    def test_0050_address_as_loggedin(self):
        "When address lookup is invoked as logged in user must succeed"
        with Transaction().start(DB_NAME, USER, CONTEXT):
            self.setup_defaults()
            app = self.get_app()

            website, = self.NereidWebsite.search([])
            country = website.countries[0]

            payment_method = self.Payment.search([])[0]
            self.Payment.write(
                [payment_method], {
                    'available_countries': [('add', [country.id])]
                }
            )

            self.NereidWebsite.write(
                [website],
                {'allowed_gateways': [('add', [payment_method])]}
            )

            # Set the country of the address of the registerd user
            address = self.registered_user.party.addresses[0]
            self.Address.write([address], {'country': country.id})

            with app.test_client() as c:
                self.login(c, 'email@example.com', 'password')
                result = c.get(
                    '/_available_gateways?'
                    'value=%d&type=address' % address
                )
                json_result = json.loads(result.data)['result']
                self.assertEqual(len(json_result), 1)


def suite():
    "Payment test suite"
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPayment))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
