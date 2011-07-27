#!/usr/bin/env python
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import json
from ast import literal_eval
from decimal import Decimal
import unittest2 as unittest

from trytond.config import CONFIG
CONFIG.options['db_type'] = 'sqlite'
from trytond.modules import register_classes
register_classes()

from nereid.testing import testing_proxy
from trytond.transaction import Transaction

class TestPayment(unittest.TestCase):
    """Test Payment Gateway"""

    @classmethod
    def setUpClass(cls):
        # Install module
        testing_proxy.install_module('nereid_payment')

        uom_obj = testing_proxy.pool.get('product.uom')
        journal_obj = testing_proxy.pool.get('account.journal')
        country_obj = testing_proxy.pool.get('country.country')
        currency_obj = testing_proxy.pool.get('currency.currency')

        with Transaction().start(testing_proxy.db_name, 1, None) as txn:
            # Create company
            cls.company = testing_proxy.create_company('Test Company')
            testing_proxy.set_company_for_user(1, cls.company)
            # Create Fiscal Year
            fiscal_year = testing_proxy.create_fiscal_year(company=cls.company)
            # Create Chart of Accounts
            testing_proxy.create_coa_minimal(cls.company)
            # Create payment term
            testing_proxy.create_payment_term()

            cls.guest_user = testing_proxy.create_guest_user(company=cls.company)

            category_template = testing_proxy.create_template(
                'category-list.jinja', ' ')
            product_template = testing_proxy.create_template(
                'product-list.jinja', ' ')
            cls.available_countries = country_obj.search([], limit=5)
            cls.available_currencies = currency_obj.search([('code', '=', 'USD')])
            cls.site = testing_proxy.create_site('testsite.com', 
                category_template = category_template,
                product_template = product_template,
                countries = [('set', cls.available_countries)],
                currencies = [('set', cls.available_currencies)])

            testing_proxy.create_template('home.jinja', ' Home ', cls.site)
            testing_proxy.create_template('checkout.jinja', 
                '{{form.errors}}', cls.site)
            testing_proxy.create_template(
                'login.jinja', 
                '{{ login_form.errors }} {{get_flashed_messages()}}', cls.site)
            testing_proxy.create_template('shopping-cart.jinja', 
                'Cart:{{ cart.id }},{{get_cart_size()|round|int}},{{cart.sale.total_amount}}', 
                cls.site)

            category = testing_proxy.create_product_category(
                'Category', uri='category')
            stock_journal = journal_obj.search([('code', '=', 'STO')])[0]
            cls.product = testing_proxy.create_product(
                'product 1', category,
                type = 'stockable',
                # purchasable = True,
                salable = True,
                list_price = Decimal('10'),
                cost_price = Decimal('5'),
                account_expense = testing_proxy.get_account_by_kind('expense'),
                account_revenue = testing_proxy.get_account_by_kind('revenue'),
                uri = 'product-1',
                sale_uom = uom_obj.search([('name', '=', 'Unit')], limit=1)[0],
                #account_journal_stock_input = stock_journal,
                #account_journal_stock_output = stock_journal,
                )

            txn.cursor.commit()

    def get_app(self, **options):
        options.update({
            'SITE': 'testsite.com',
            'GUEST_USER': self.guest_user,
            })
        return testing_proxy.make_app(**options)

    def setUp(self):
        self.sale_obj = testing_proxy.pool.get('sale.sale')
        self.country_obj = testing_proxy.pool.get('country.country')
        self.address_obj = testing_proxy.pool.get('party.address')
        self.website_obj = testing_proxy.pool.get('nereid.website')
        self.payment_obj = testing_proxy.pool.get('nereid.payment.gateway')

    def test_0010_check_cart(self):
        """Assert nothing broke the cart."""
        app = self.get_app()
        with app.test_client() as c:
            rv = c.get('/en_US/cart')
            self.assertEqual(rv.status_code, 200)

            c.post('/en_US/cart/add', data={
                'product': self.product, 'quantity': 5
                })
            rv = c.get('/en_US/cart')
            self.assertEqual(rv.status_code, 200)

        with Transaction().start(testing_proxy.db_name, testing_proxy.user, None):
            sales_ids = self.sale_obj.search([])
            self.assertEqual(len(sales_ids), 1)
            sale = self.sale_obj.browse(sales_ids[0])
            self.assertEqual(len(sale.lines), 1)
            self.assertEqual(sale.lines[0].product.id, self.product)

    def test_0020_find_gateways(self):
        app = self.get_app()
        with app.test_client() as c:
            rv = c.get('/en_US/_available_gateways?value=777666554')
            self.assertEqual(json.loads(rv.data), {u'result': []})

    def test_0030_find_after_adding_country(self):
        with Transaction().start(testing_proxy.db_name, 
                testing_proxy.user, testing_proxy.context) as txn:

            website_id, = self.website_obj.search([])
            website = self.website_obj.browse(website_id)
            payment_method_id = self.payment_obj.search([])[0]
            self.payment_obj.write(payment_method_id, {
                'available_countries': [('add', [c.id for c in website.countries])]
                })
            country_id = website.countries[0].id
            txn.cursor.commit()

        app = self.get_app()
        with app.test_client() as c:
            result = c.get('/en_US/_available_gateways?value=%s' % country_id)
            # False because its not added to website
            self.assertFalse(
                payment_method_id in json.loads(result.data)['result']
                )

        with Transaction().start(testing_proxy.db_name, 
                testing_proxy.user, testing_proxy.context) as txn:
            self. website_obj.write(website_id, 
                {'allowed_gateways': [('add', [payment_method_id])]})
            txn.cursor.commit()

        app = self.get_app()
        with app.test_client() as c:
            result = c.get('/en_US/_available_gateways?value=%s' % country_id)
            result_tuples = json.loads(result.data)['result']
            self.assertEqual(len(result_tuples), 1)
            self.assertTrue(
                payment_method_id in [t[0] for t in result_tuples]
                )

    def test_0040_address_as_guest(self):
        "When address lookup is invoked as guest it should fail"
        with Transaction().start(testing_proxy.db_name, 
                testing_proxy.user, testing_proxy.context) as txn:
            website_id, = self.website_obj.search([])
            website = self.website_obj.browse(website_id)
            country_id = website.countries[0].id
            txn.cursor.commit()

        app = self.get_app()
        with app.test_client() as c:
            result = c.get('/en_US/_available_gateways?value=1&type=address')
            # False because its not added to website
            self.assertEqual(result.status_code, 403)

    def test_0050_address_as_loggedin(self):
        "When address lookup is invoked as logged in user must succeed"
        with Transaction().start(testing_proxy.db_name, 
                testing_proxy.user, testing_proxy.context) as txn:
            website_id, = self.website_obj.search([])
            website = self.website_obj.browse(website_id)
            country_id = website.countries[0].id
            regd_user_id = testing_proxy.create_user_party('Registered User', 
                'email@example.com', 'password', company=self.company)
            self.address_obj.write(regd_user_id, {'country': country_id})
            txn.cursor.commit()

        app = self.get_app()
        with app.test_client() as c:
            rv = c.post('/en_US/login', 
                data={'email': 'email@example.com', 'password': 'password'})
            result = c.get(
                '/en_US/_available_gateways?value=%s&type=address' % regd_user_id)
            result_tuples = json.loads(result.data)['result']
            self.assertEqual(len(result_tuples), 1)


def suite():
    "Payment test suite"
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPayment))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
