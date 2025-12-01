from trytond.pool import Pool
from . import party


def register():
    Pool.register(
        party.Identifier,
        module='party_ge_identifier', type_='model'
    )
