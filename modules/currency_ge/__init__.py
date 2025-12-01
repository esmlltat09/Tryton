from trytond.pool import Pool
from . import currency


def register():
    Pool.register(
        currency.Cron,
        currency.Currency,
        module='currency_ge',
        type_='model',
    )
