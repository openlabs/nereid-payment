nereid-payment (DEPRECATED)
===========================

nereid-payment module is deprecated on behalf of the
`payment-gateway <https://github.com/openlabs/payment-gateway>`_ module
which has a better API and works natively on Tryton without nereid.

.. image:: https://travis-ci.org/openlabs/nereid-payment.png?branch=develop
  :target: https://travis-ci.org/openlabs/nereid-payment

.. image:: https://coveralls.io/repos/openlabs/nereid-payment/badge.png
  :target: https://coveralls.io/r/openlabs/nereid-payment

Then why is this module here ?
------------------------------

If you are migrating from an older version of nereid-webshop or you were
using this module to process payments in versions before 3.0, it is
likely that you still want to see the old transactions and records. So
this module leaves behind the database tables and views which will allow
you to view those old records and manually take actions.

Can I Still process payments with this module ?
-----------------------------------------------

Yes and No!

Yes, because you can manually process any transactions from the Tryton
client interface. This should let you complete those orders which may be
in-progress when you decided to migrate to the newer version of Tryton
(and webshop).

No, because the checkout module does not implement this API anymore and
you wont be able to process payment using this module. Checkout uses the
new `payment-gateway <https://github.com/openlabs/payment-gateway>`_
module.

How long will this module be maintained ?
-----------------------------------------

The module will be maintained in this state until version 3.4 of Tryton.

Can we not just discard the transactions ?
------------------------------------------

Yes, the transactions can safely be discarded after a certain time. The
transactions themselves hold only the specific information related to the
payment gateway interaction itself. The account move and related details
are stored in the models provided by the accounting modules of Tryton.

I need help with this
---------------------

This module is professionally supported by `Openlabs <http://www.openlabs.co.in>`_.
If you are looking for on-site teaching or consulting support, contact our
`sales <mailto:sales@openlabs.co.in>`_ and `support
<mailto:support@openlabs.co.in>`_ teams.
