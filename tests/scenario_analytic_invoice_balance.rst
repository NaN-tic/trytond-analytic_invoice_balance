=================================
Analytic Invoice Balance Scenario
=================================

Imports::

    >>> import datetime
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install analytic_invoice_balance::

    >>> Module = Model.get('ir.module')
    >>> analytic_invoice_module, = Module.find(
    ...     [('name', '=', 'analytic_invoice_balance')])
    >>> analytic_invoice_module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> receivable = accounts['receivable']
    >>> tax_account = accounts['tax']

Create two revenue subaccounts::

    >>> Account = Model.get('account.account')
    >>> revenue1 = Account(Account.copy([revenue.id], config.context)[0])
    >>> revenue1.name = 'Revenue 1'
    >>> revenue1.parent = revenue
    >>> revenue1.save()
    >>> revenue2 = Account(Account.copy([revenue1.id], config.context)[0])
    >>> revenue2.name = 'Revenue 2'
    >>> revenue2.save()

Create two expense subaccounts::

    >>> expense1 = Account(Account.copy([expense.id], config.context)[0])
    >>> expense1.name = 'Revenue 1'
    >>> expense1.parent = expense
    >>> expense1.save()
    >>> expense2 = Account(Account.copy([expense1.id], config.context)[0])
    >>> expense2.name = 'Revenue 2'
    >>> expense2.save()

Create tax::

    >>> Tax = Model.get('account.tax')
    >>> tax = set_tax_code(create_tax(Decimal('.21')))
    >>> tax.save()

Create analytic accounts::

    >>> AnalyticAccount = Model.get('analytic_account.account')
    >>> root = AnalyticAccount(type='root', name='Root')
    >>> root.save()
    >>> analytic_account1 = AnalyticAccount(root=root, parent=root,
    ...     name='Analytic 1')
    >>> analytic_account1.save()
    >>> analytic_account2 = AnalyticAccount(root=root, parent=root,
    ...     name='Analytic 2')
    >>> analytic_account2.save()

Configure analytic required in accounts::

    >>> revenue.analytic_required.append(AnalyticAccount(root.id))
    >>> revenue.save()
    >>> revenue1.analytic_required.append(AnalyticAccount(root.id))
    >>> revenue1.save()
    >>> revenue2.analytic_required.append(AnalyticAccount(root.id))
    >>> revenue2.save()
    >>> receivable.analytic_optional.append(AnalyticAccount(root.id))
    >>> receivable.save()
    >>> tax_account.analytic_forbidden.append(AnalyticAccount(root.id))
    >>> tax_account.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='30% + Remainder')
    >>> percent_line = payment_term.lines.new(type='percent_on_total')
    >>> percent_line.ratio = Decimal('0.3000')
    >>> _ = payment_term.lines.new(type='remainder')
    >>> payment_term.save()

Create invoice with analytic accounts::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice1 = Invoice()
    >>> invoice1.party = party
    >>> invoice1.payment_term = payment_term
    >>> line = invoice1.lines.new()
    >>> line.account = revenue1
    >>> line.description = 'Revenue 1'
    >>> entry, = line.analytic_accounts
    >>> entry.root == root
    True
    >>> entry.account = analytic_account1
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('125.55')
    >>> line.taxes.append(Tax(tax.id))
    >>> line = invoice1.lines.new()
    >>> line.account = revenue2
    >>> line.description = 'Revenue 2'
    >>> entry, = line.analytic_accounts
    >>> entry.account = analytic_account2
    >>> line.quantity = 6
    >>> line.unit_price = Decimal('25')
    >>> line.taxes.append(Tax(tax.id))
    >>> invoice1.click('post')
    >>> invoice1.state
    u'posted'

Check amounts::

    >>> invoice1.untaxed_amount
    Decimal('275.55')
    >>> invoice1.tax_amount
    Decimal('57.87')
    >>> invoice1.total_amount
    Decimal('333.42')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('125.55')
    >>> analytic_account1.debit
    Decimal('151.92')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('150.00')
    >>> analytic_account2.debit
    Decimal('181.50')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.debit) for ml in invoice1.move.lines
    ...     for al in ml.analytic_lines if ml.account == invoice1.account)
    [(u'Analytic 1', Decimal('45.58')), (u'Analytic 1', Decimal('106.34')), (u'Analytic 2', Decimal('54.45')), (u'Analytic 2', Decimal('127.05'))]

Create invoice with amounts with rounding problems (the analytic amount for
both payments round to 0)::

    >>> invoice2 = Invoice()
    >>> invoice2.party = party
    >>> invoice2.payment_term = payment_term
    >>> line = invoice2.lines.new()
    >>> line.account = revenue1
    >>> line.description = 'Revenue 1-2'
    >>> entry, = line.analytic_accounts
    >>> entry.root == root
    True
    >>> entry.account = analytic_account1
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('0.01')
    >>> line = invoice2.lines.new()
    >>> line.account = revenue2
    >>> line.description = 'Revenue 2-2'
    >>> entry, = line.analytic_accounts
    >>> entry.account = analytic_account2
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('0.01')
    >>> invoice2.click('post')
    >>> invoice2.state
    u'posted'

Check amounts::

    >>> invoice2.untaxed_amount
    Decimal('0.02')
    >>> invoice2.tax_amount
    Decimal('0.0')
    >>> invoice2.total_amount
    Decimal('0.02')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('125.56')
    >>> analytic_account1.debit
    Decimal('151.93')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('150.01')
    >>> analytic_account2.debit
    Decimal('181.51')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.debit) for ml in invoice2.move.lines
    ...     for al in ml.analytic_lines if ml.account == invoice2.account)
    [(u'Analytic 1', Decimal('0.01')), (u'Analytic 2', Decimal('0.01'))]

Create invoice with amounts with rounding problems (the analytic amount for
first payment round to 0 and for second payment is greater than pending
amount)::

    >>> invoice3 = Invoice()
    >>> invoice3.party = party
    >>> invoice3.payment_term = payment_term
    >>> line = invoice3.lines.new()
    >>> line.account = revenue1
    >>> line.description = 'Revenue 1-3'
    >>> entry, = line.analytic_accounts
    >>> entry.root == root
    True
    >>> entry.account = analytic_account1
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('0.015')
    >>> line = invoice3.lines.new()
    >>> line.account = revenue2
    >>> line.description = 'Revenue 2-2'
    >>> entry, = line.analytic_accounts
    >>> entry.account = analytic_account2
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('0.0151')
    >>> invoice3.click('post')
    >>> invoice3.state
    u'posted'

Check amounts::

    >>> invoice3.untaxed_amount
    Decimal('0.04')
    >>> invoice3.tax_amount
    Decimal('0.0')
    >>> invoice3.total_amount
    Decimal('0.04')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('125.58')
    >>> analytic_account1.debit
    Decimal('151.95')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('150.03')
    >>> analytic_account2.debit
    Decimal('181.53')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.debit) for ml in invoice3.move.lines
    ...     for al in ml.analytic_lines if ml.account == invoice3.account)
    [(u'Analytic 1', Decimal('0.01')), (u'Analytic 1', Decimal('0.01')), (u'Analytic 2', Decimal('0.02'))]

Credit first invoice with refund::

    >>> credit_wizard1 = Wizard('account.invoice.credit', [invoice1])
    >>> credit_wizard1.form.with_refund = True
    >>> credit_wizard1.execute('credit')
    >>> invoice1.reload()
    >>> invoice1.state
    u'paid'

Check credit invoice amounts::

    >>> credit_invoice1, = Invoice.find([
    ...         ('lines.origin.invoice', '=', invoice1.id,
    ...             'account.invoice.line'),
    ...         ])
    >>> credit_invoice1.untaxed_amount
    Decimal('-275.55')
    >>> credit_invoice1.tax_amount
    Decimal('-57.87')
    >>> credit_invoice1.total_amount
    Decimal('-333.42')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('277.50')
    >>> analytic_account1.debit
    Decimal('277.50')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('331.53')
    >>> analytic_account2.debit
    Decimal('331.53')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.credit) for ml in credit_invoice1.move.lines
    ...     for al in ml.analytic_lines if ml.account == credit_invoice1.account)
    [(u'Analytic 1', Decimal('45.58')), (u'Analytic 1', Decimal('106.34')), (u'Analytic 2', Decimal('54.45')), (u'Analytic 2', Decimal('127.05'))]

Credit second invoice with refund::

    >>> credit_wizard2 = Wizard('account.invoice.credit', [invoice2])
    >>> credit_wizard2.form.with_refund = True
    >>> credit_wizard2.execute('credit')
    >>> invoice2.reload()
    >>> invoice2.state
    u'paid'

Check credit invoice amounts::

    >>> credit_invoice2, = Invoice.find([
    ...         ('lines.origin.invoice', '=', invoice2.id,
    ...             'account.invoice.line'),
    ...         ])
    >>> credit_invoice2.untaxed_amount
    Decimal('-0.02')
    >>> credit_invoice2.tax_amount
    Decimal('0.0')
    >>> credit_invoice2.total_amount
    Decimal('-0.02')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('277.51')
    >>> analytic_account1.debit
    Decimal('277.51')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('331.54')
    >>> analytic_account2.debit
    Decimal('331.54')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.credit) for ml in credit_invoice2.move.lines
    ...     for al in ml.analytic_lines if ml.account == credit_invoice2.account)
    [(u'Analytic 1', Decimal('0.01')), (u'Analytic 2', Decimal('0.01'))]

Credit third invoice with refund::

    >>> credit_wizard3 = Wizard('account.invoice.credit', [invoice3])
    >>> credit_wizard3.form.with_refund = True
    >>> credit_wizard3.execute('credit')
    >>> invoice3.reload()
    >>> invoice3.state
    u'paid'

Check credit invoice amounts::

    >>> credit_invoice3, = Invoice.find([
    ...         ('lines.origin.invoice', '=', invoice3.id,
    ...             'account.invoice.line'),
    ...         ])
    >>> credit_invoice3.untaxed_amount
    Decimal('-0.04')
    >>> credit_invoice3.tax_amount
    Decimal('0.0')
    >>> credit_invoice3.total_amount
    Decimal('-0.04')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('277.53')
    >>> analytic_account1.debit
    Decimal('277.53')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('331.56')
    >>> analytic_account2.debit
    Decimal('331.56')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.credit) for ml in credit_invoice3.move.lines
    ...     for al in ml.analytic_lines if ml.account == credit_invoice3.account)
    [(u'Analytic 1', Decimal('0.01')), (u'Analytic 1', Decimal('0.01')), (u'Analytic 2', Decimal('0.02'))]

Create a supplier invoice with rounding problems::

    >>> supplier_inv1 = Invoice()
    >>> supplier_inv1.type = 'in'
    >>> supplier_inv1.party = party
    >>> supplier_inv1.payment_term = payment_term
    >>> supplier_inv1.invoice_date = today
    >>> line = supplier_inv1.lines.new()
    >>> line.account = expense1
    >>> line.description = 'Expense 1'
    >>> entry, = line.analytic_accounts
    >>> entry.root == root
    True
    >>> entry.account = analytic_account1
    >>> line.quantity = 4
    >>> line.unit_price = Decimal('25')
    >>> line.taxes.append(Tax(tax.id))
    >>> line = supplier_inv1.lines.new()
    >>> line.account = expense2
    >>> line.description = 'Expense 2'
    >>> entry, = line.analytic_accounts
    >>> entry.account = analytic_account2
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('0.01')
    >>> line.taxes.append(Tax(tax.id))
    >>> supplier_inv1.click('post')
    >>> supplier_inv1.state
    u'posted'

Check amounts::

    >>> supplier_inv1.untaxed_amount
    Decimal('100.01')
    >>> supplier_inv1.tax_amount
    Decimal('21.00')
    >>> supplier_inv1.total_amount
    Decimal('121.01')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('398.53')
    >>> analytic_account1.debit
    Decimal('377.53')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('331.57')
    >>> analytic_account2.debit
    Decimal('331.57')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.credit) for ml in supplier_inv1.move.lines
    ...     for al in ml.analytic_lines if ml.account == supplier_inv1.account)
    [(u'Analytic 1', Decimal('36.30')), (u'Analytic 1', Decimal('84.70')), (u'Analytic 2', Decimal('0.01'))]

Create a supplier invoice with different rounding problems::

    >>> supplier_inv2 = Invoice()
    >>> supplier_inv2.type = 'in'
    >>> supplier_inv2.party = party
    >>> supplier_inv2.payment_term = payment_term
    >>> supplier_inv2.invoice_date = today
    >>> line = supplier_inv2.lines.new()
    >>> line.account = expense1
    >>> line.description = 'Expense 1-2'
    >>> entry, = line.analytic_accounts
    >>> entry.root == root
    True
    >>> entry.account = analytic_account1
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('0.015')
    >>> line = supplier_inv2.lines.new()
    >>> line.account = expense2
    >>> line.description = 'Expense 2-2'
    >>> entry, = line.analytic_accounts
    >>> entry.account = analytic_account2
    >>> line.quantity = 1
    >>> line.unit_price = Decimal('0.0151')
    >>> supplier_inv2.click('post')
    >>> supplier_inv2.state
    u'posted'

Check amounts::

    >>> supplier_inv2.untaxed_amount
    Decimal('0.04')
    >>> supplier_inv2.tax_amount
    Decimal('0.0')
    >>> supplier_inv2.total_amount
    Decimal('0.04')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('398.55')
    >>> analytic_account1.debit
    Decimal('377.55')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('331.59')
    >>> analytic_account2.debit
    Decimal('331.59')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.credit) for ml in supplier_inv2.move.lines
    ...     for al in ml.analytic_lines if ml.account == supplier_inv2.account)
    [(u'Analytic 1', Decimal('0.01')), (u'Analytic 1', Decimal('0.01')), (u'Analytic 2', Decimal('0.02'))]

Credit first supplier invoice and post it::

    >>> credit_wizard4 = Wizard('account.invoice.credit', [supplier_inv1])
    >>> credit_wizard4.execute('credit')
    >>> credit_supplier_inv1, = Invoice.find([
    ...         ('lines.origin.invoice', '=', supplier_inv1.id,
    ...             'account.invoice.line'),
    ...         ])
    >>> credit_supplier_inv1.invoice_date = today
    >>> credit_supplier_inv1.click('post')
    >>> credit_supplier_inv1.state
    u'posted'

Check credit invoice amounts::

    >>> credit_supplier_inv1.untaxed_amount
    Decimal('-100.01')
    >>> credit_supplier_inv1.tax_amount
    Decimal('-21.00')
    >>> credit_supplier_inv1.total_amount
    Decimal('-121.01')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('498.55')
    >>> analytic_account1.debit
    Decimal('498.55')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('331.60')
    >>> analytic_account2.debit
    Decimal('331.60')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.debit) for ml in credit_supplier_inv1.move.lines
    ...     for al in ml.analytic_lines if ml.account == credit_supplier_inv1.account)
    [(u'Analytic 1', Decimal('36.30')), (u'Analytic 1', Decimal('84.70')), (u'Analytic 2', Decimal('0.01'))]

Credit second supplier invoice and post it::

    >>> credit_wizard5 = Wizard('account.invoice.credit', [supplier_inv2])
    >>> credit_wizard5.execute('credit')
    >>> credit_supplier_inv2, = Invoice.find([
    ...         ('lines.origin.invoice', '=', supplier_inv2.id,
    ...             'account.invoice.line'),
    ...         ])
    >>> credit_supplier_inv2.invoice_date = today
    >>> credit_supplier_inv2.click('post')
    >>> credit_supplier_inv2.state
    u'posted'

Check credit invoice amounts::

    >>> credit_supplier_inv2.untaxed_amount
    Decimal('-0.04')
    >>> credit_supplier_inv2.tax_amount
    Decimal('0.0')
    >>> credit_supplier_inv2.total_amount
    Decimal('-0.04')

Check analytic amounts::

    >>> analytic_account1.reload()
    >>> analytic_account1.credit
    Decimal('498.57')
    >>> analytic_account1.debit
    Decimal('498.57')
    >>> analytic_account2.reload()
    >>> analytic_account2.credit
    Decimal('331.62')
    >>> analytic_account2.debit
    Decimal('331.62')

Check analytics in balance move lines::

    >>> sorted((al.account.name, al.debit) for ml in credit_supplier_inv2.move.lines
    ...     for al in ml.analytic_lines if ml.account == credit_supplier_inv2.account)
    [(u'Analytic 1', Decimal('0.01')), (u'Analytic 1', Decimal('0.01')), (u'Analytic 2', Decimal('0.02'))]
