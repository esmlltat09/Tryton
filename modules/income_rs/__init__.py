from trytond.pool import Pool
from .income import IncomeDeclaration, IncomeDeclarationLine


def register():
    Pool.register(
        IncomeDeclaration,
        IncomeDeclarationLine,
        module='income_rs', type_='model'
    )
