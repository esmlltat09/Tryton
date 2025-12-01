from trytond.pool import Pool
from . import payroll


def register():
    Pool.register(
        payroll.Contract,
        payroll.Payslip,
        payroll.PayslipLine,
        module='hr_payroll', type_='model',
    )
