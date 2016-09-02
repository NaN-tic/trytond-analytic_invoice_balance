# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.analytic_invoice_balance.tests\
        .test_analytic_invoice_balance import suite
except ImportError:
    from .test_analytic_invoice_balance import suite

__all__ = ['suite']
