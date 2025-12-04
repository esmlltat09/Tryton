from trytond.pool import PoolMeta
from trytond.model import fields

__all__ = ['AccountTypeTemplate', 'AccountType']


class AccountTypeTemplate(metaclass=PoolMeta):
    __name__ = 'account.account.type.template'

    display_balance = fields.Selection([
        ('debit-credit', 'Debit - Credit'),
        ('credit-debit', 'Credit - Debit'),
    ], "Display Balance", required=False)

    assets = fields.Boolean("Assets")
    receivable = fields.Boolean("Receivable")
    payable = fields.Boolean("Payable")
    stock = fields.Boolean("Stock")
    fixed_asset = fields.Boolean("Fixed Asset")
    revenue = fields.Boolean("Revenue")
    expense = fields.Boolean("Expense")

    def _get_type_value(self, type=None):
        values = super()._get_type_value(type)

        # --- გადამრჩენელი კოდი ---
        # თუ სისტემა ხედავს, რომ ბალანსი ცარიელია (None), 
        # ძალით ვუწერთ 'debit-credit'-ს, რომ არ გაჭედოს.
        if not values.get('display_balance'):
            values['display_balance'] = 'debit-credit'
        # -------------------------

        if not type or type.assets != self.assets:
            values['assets'] = self.assets
        if not type or type.receivable != self.receivable:
            values['receivable'] = self.receivable
        if not type or type.payable != self.payable:
            values['payable'] = self.payable
        if not type or type.stock != self.stock:
            values['stock'] = self.stock
        if not type or type.fixed_asset != self.fixed_asset:
            values['fixed_asset'] = self.fixed_asset
        if not type or type.revenue != self.revenue:
            values['revenue'] = self.revenue
        if not type or type.expense != self.expense:
            values['expense'] = self.expense

        return values


class AccountType(metaclass=PoolMeta):
    __name__ = 'account.account.type'

    display_balance = fields.Selection([
        ('debit-credit', 'Debit - Credit'),
        ('credit-debit', 'Credit - Debit'),
    ], "Display Balance", required=False)

    assets = fields.Boolean("Assets")
    receivable = fields.Boolean("Receivable")
    payable = fields.Boolean("Payable")
    stock = fields.Boolean("Stock")
    fixed_asset = fields.Boolean("Fixed Asset")
    revenue = fields.Boolean("Revenue")
    expense = fields.Boolean("Expense")