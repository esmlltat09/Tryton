from trytond.pool import Pool
from . import account

def register():
    Pool.register(
        account.AccountTypeTemplate,
        account.AccountType,
        module='account_ge', type_='model'
    )