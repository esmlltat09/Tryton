from trytond.pool import PoolMeta
from trytond.model import fields

# 1. ველები შაბლონისთვის
class AccountTypeTemplate(metaclass=PoolMeta):
    __name__ = 'account.account.type.template'

    assets = fields.Boolean("Assets")
    receivable = fields.Boolean("Receivable")
    payable = fields.Boolean("Payable")
    stock = fields.Boolean("Stock")
    fixed_asset = fields.Boolean("Fixed Asset")
    
    # ეს ველები აკლდა თქვენს ფაილს:
    revenue = fields.Boolean("Revenue")
    expense = fields.Boolean("Expense")

    # ეს ველი აკლდა (ამიტომ ქრაშავდა):
    display_balance = fields.Selection([
        ('debit-credit', 'Debit - Credit'),
        ('credit-debit', 'Credit - Debit'),
        ], "Display Balance")

# 2. ველები რეალური ტიპისთვის
class AccountType(metaclass=PoolMeta):
    __name__ = 'account.account.type'

    assets = fields.Boolean("Assets")
    receivable = fields.Boolean("Receivable")
    payable = fields.Boolean("Payable")
    stock = fields.Boolean("Stock")
    fixed_asset = fields.Boolean("Fixed Asset")
    
    revenue = fields.Boolean("Revenue")
    expense = fields.Boolean("Expense")

    display_balance = fields.Selection([
        ('debit-credit', 'Debit - Credit'),
        ('credit-debit', 'Credit - Debit'),
        ], "Display Balance")

    def _get_type_value(self, template):
        values = super(AccountType, self)._get_type_value(template)
        values['assets'] = template.assets
        values['receivable'] = template.receivable
        values['payable'] = template.payable
        values['stock'] = template.stock
        values['fixed_asset'] = template.fixed_asset
        
        # ამათი გადატანაც აუცილებელია:
        values['revenue'] = template.revenue
        values['expense'] = template.expense
        values['display_balance'] = template.display_balance
        return values