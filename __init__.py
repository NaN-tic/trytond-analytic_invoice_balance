# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

from .invoice import Invoice


def register():
    Pool.register(
        Invoice,
        module='analytic_invoice_balance', type_='model')
