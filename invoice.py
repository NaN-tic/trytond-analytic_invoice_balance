# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.pool import Pool, PoolMeta

__all__ = ['Invoice']


class Invoice:
    __name__ = 'account.invoice'
    __metaclass__ = PoolMeta

    def get_move(self):
        Tax = Pool().get('account.tax')

        move = super(Invoice, self).get_move()
        if not self.total_amount:
            return move

        total_amount = self.total_amount
        sign = (Decimal(-1) if (self.type == 'out'
                and self.total_amount < Decimal(0)
                or self.type == 'in' and self.total_amount >= Decimal(0))
            else Decimal(1))

        aa2amount = {}
        for line in move.lines:
            for analytic_line in getattr(line, 'analytic_lines', []):
                if not analytic_line.credit and not analytic_line.debit:
                    continue
                root_id = analytic_line.account.root.id
                account_id = analytic_line.account.id
                aa2amount.setdefault(root_id, {})
                aa2amount[root_id].setdefault(account_id, {
                        'credit': Decimal(0),
                        'debit': Decimal(0),
                        'pending_amount': Decimal(0),
                        })
                # It puts the credit to debit and debit to credit because the
                # receivable/payable amounts has the inverse condition than
                # revenue/expense ones
                if analytic_line.credit:
                    aa2amount[root_id][account_id]['debit'] += (
                        analytic_line.credit)
                    aa2amount[root_id][account_id]['pending_amount'] += (
                        analytic_line.credit * sign)
                    for values in Tax.compute(
                            [tl.tax for tl in getattr(line, 'tax_lines', [])],
                            analytic_line.credit, 1):
                        tax_amount = self.currency.round(values['amount'])
                        aa2amount[root_id][account_id]['debit'] += tax_amount
                        aa2amount[root_id][account_id]['pending_amount'] += (
                            tax_amount * sign)
                if analytic_line.debit:
                    aa2amount[root_id][account_id]['credit'] += (
                        analytic_line.debit)
                    aa2amount[root_id][account_id]['pending_amount'] -= (
                        analytic_line.debit * sign)
                    for values in Tax.compute(
                            [tl.tax for tl in getattr(line, 'tax_lines', [])],
                            analytic_line.debit, 1):
                        tax_amount = self.currency.round(values['amount'])
                        aa2amount[root_id][account_id]['credit'] += tax_amount
                        aa2amount[root_id][account_id]['pending_amount'] -= (
                            tax_amount * sign)

        if aa2amount:
            for line in move.lines:
                if line.account != self.account:
                    # it isn't receivable/payable move line
                    continue

                analytic_lines = []
                amount = line.debit - line.credit
                line_ratio = amount / total_amount
                for root_values in aa2amount.itervalues():
                    pending_amount = amount * sign
                    aa2anal_line = {}
                    for aa_id, aa_values in root_values.iteritems():
                        credit = self.company.currency.round(
                            aa_values['credit'] * line_ratio)
                        if (credit > -self.company.currency.rounding
                                and credit < self.company.currency.rounding):
                            credit = Decimal(0)
                        debit = self.company.currency.round(
                            aa_values['debit'] * line_ratio)
                        if (debit > -self.company.currency.rounding
                                and debit < self.company.currency.rounding):
                            debit = Decimal(0)
                        if not credit and not debit:
                            continue

                        pending_amount += credit * sign
                        pending_amount -= debit * sign
                        aa_values['pending_amount'] += credit * sign
                        aa_values['pending_amount'] -= debit * sign
                        if credit < Decimal(0) or debit < Decimal(0):
                            credit, debit = abs(debit), abs(credit)
                        aa2anal_line[aa_id] = self.get_invice_analytic_entry(
                            line, aa_id, debit, credit)

                    if pending_amount != Decimal(0):
                        for aa_id, aa_values in root_values.iteritems():
                            if aa_values['pending_amount'] == Decimal(0):
                                continue
                            elif pending_amount <= aa_values['pending_amount']:
                                aa_amount = pending_amount
                                aa_values['pending_amount'] -= pending_amount
                                pending_amount = Decimal(0)
                            else:
                                aa_amount = aa_values['pending_amount']
                                pending_amount -= aa_values['pending_amount']
                                aa_values['pending_amount'] = Decimal(0)
                            if aa_id in aa2anal_line:
                                if sign < Decimal(0):
                                    if aa2anal_line[aa_id].credit:
                                        aa2anal_line[aa_id].credit += aa_amount
                                    elif aa2anal_line[aa_id].debit > aa_amount:
                                        aa2anal_line[aa_id].debit -= aa_amount
                                    elif aa2anal_line[aa_id].debit < aa_amount:
                                        aa2anal_line[aa_id].credit = (aa_amount
                                            - aa2anal_line[aa_id].debit)
                                        aa2anal_line[aa_id].debit = Decimal(0)
                                    else:  # aa_amount == anal_line debit
                                        del aa2anal_line[aa_id]
                                else:
                                    if aa2anal_line[aa_id].debit:
                                        aa2anal_line[aa_id].debit += aa_amount
                                    elif (aa2anal_line[aa_id].credit
                                            > aa_amount):
                                        aa2anal_line[aa_id].credit -= aa_amount
                                    elif (aa2anal_line[aa_id].credit
                                            < aa_amount):
                                        aa2anal_line[aa_id].debit = (aa_amount
                                            - aa2anal_line[aa_id].credit)
                                        aa2anal_line[aa_id].credit = Decimal(0)
                                    else:  # aa_amount == anal_line credit
                                        del aa2anal_line[aa_id]
                            else:
                                aa2anal_line[aa_id] = (
                                    self.get_invice_analytic_entry(
                                        line,
                                        aa_id,
                                        (aa_amount
                                            if sign >= Decimal(0)
                                            else Decimal(0)),
                                        (aa_amount
                                            if sign < Decimal(0)
                                            else Decimal(0))))
                            if pending_amount == Decimal(0):
                                break
                    analytic_lines += aa2anal_line.values()
                line.analytic_lines = analytic_lines
        return move

    def get_invice_analytic_entry(self, move_line, analytic_account_id, debit,
            credit):
        assert (debit == Decimal(0)) or (credit == Decimal(0)), (
            "Debit (%s) or Credit (%s) must to be 0: move_line=%s"
            % (debit, credit, move_line._save_values))
        pool = Pool()
        AnalyticAccount = pool.get('analytic_account.account')
        AnalyticLine = pool.get('analytic_account.line')

        analytic_line = AnalyticLine()
        analytic_line.name = '%s (%s)' % (
            self.number, move_line.maturity_date)
        analytic_line.debit = debit
        analytic_line.credit = credit
        analytic_line.account = AnalyticAccount(analytic_account_id)
        analytic_line.journal = self.journal
        analytic_line.date = move_line.maturity_date
        analytic_line.reference = self.reference
        analytic_line.party = self.party
        analytic_line.internal_company = self.company
        return analytic_line
