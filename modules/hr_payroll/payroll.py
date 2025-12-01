import calendar
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from trytond.model import ModelSQL, ModelView, Workflow, fields
from trytond.pyson import Eval
from trytond.pool import Pool


def round_amount(value):
    """დამრგვალება 2 ათწილადზე."""
    if value is None:
        return None
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def count_business_days(start_date, end_date, holidays=None):
    """
    ითვლის სამუშაო დღეებს (ორშაბათი-პარასკევი), გამოკლებით დღესასწაულებისა.
    """
    if not start_date or not end_date:
        return 0

    if holidays is None:
        holidays = set()

    days = 0
    current = start_date
    while current <= end_date:
        # 0=ორშაბათი ... 4=პარასკევი
        if current.weekday() < 5 and current not in holidays:
            days += 1
        current += timedelta(days=1)
    return days


class Contract(ModelSQL, ModelView):
    "Employee Contract"
    __name__ = 'hr.contract'

    company = fields.Many2One(
        'company.company', "Company", required=True)
    employee = fields.Many2One(
        'company.employee', "Employee", required=True)

    start_date = fields.Date("Start Date", required=True)
    end_date = fields.Date("End Date")

    wage = fields.Numeric(
        "Monthly Wage", digits=(16, 2), required=True)

    currency = fields.Many2One(
        'currency.currency', "Currency", required=True)

    journal = fields.Many2One(
        'account.journal', "Payroll Journal")

    # --- ანგარიშები ---
    expense_account = fields.Many2One(
        'account.account', "Salary Expense Account",
        domain=[('type', '=', 'expense')])

    payable_account = fields.Many2One(
        'account.account', "Salary Payable Account",
        domain=[('type', '=', 'payable')])

    tax_account = fields.Many2One(
        'account.account', "Income Tax Account",
        domain=[('type', '=', 'payable')])

    pension_account = fields.Many2One(
        'account.account', "Pension Account",
        domain=[('type', '=', 'payable')])

    employer_pension_expense_account = fields.Many2One(
        'account.account', "Employer Pension Expense Account",
        domain=[('type', '=', 'expense')])

    # --- პარამეტრები ---
    pension_participant = fields.Boolean("Pension Participant")
    active = fields.Boolean("Active")

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_pension_participant():
        return True

    @staticmethod
    def default_currency():
        """
        კონტრაქტის ვალუტა დეფოლტად კომპანიის ვალუტა.
        """
        Company = Pool().get('company.company')
        companies = Company.search([], limit=1)
        if companies:
            return companies[0].currency.id
        return None


class Payslip(Workflow, ModelSQL, ModelView):
    "Employee Payslip"
    __name__ = 'hr.payslip'

    company = fields.Many2One(
        'company.company', "Company", required=True,
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])

    employee = fields.Many2One(
        'company.employee', "Employee", required=True,
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])

    contract = fields.Many2One(
        'hr.contract', "Contract", required=True,
        domain=[
            ('employee', '=', Eval('employee')),
            ('company', '=', Eval('company')),
            ('active', '=', True),
        ],
        states={'readonly': Eval('state') != 'draft'},
        depends=['state', 'employee', 'company'])

    date_from = fields.Date(
        "From", required=True,
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])
    date_to = fields.Date(
        "To", required=True,
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])

    # --- დღეები ---
    working_days = fields.Integer(
        "Working Days", readonly=True,
        help="Actual business days (Mon-Fri, excluding public holidays).")

    paid_days = fields.Integer(
        "Paid Days",
        help="Days to pay salary for. If empty, equals Working Days.",
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])

    # --- თანხები ---
    gross = fields.Numeric("Gross Salary", digits=(16, 2), readonly=True)
    pension_employee = fields.Numeric(
        "Pension (Employee)", digits=(16, 2), readonly=True)
    pension_employer = fields.Numeric(
        "Pension (Employer)", digits=(16, 2), readonly=True)
    income_tax = fields.Numeric(
        "Income Tax", digits=(16, 2), readonly=True)
    net = fields.Numeric("Net Salary", digits=(16, 2), readonly=True)

    currency = fields.Many2One(
        'currency.currency', "Currency", required=True)

    state = fields.Selection([
        ('draft', "Draft"),
        ('done', "Done"),
        ('cancelled', "Cancelled"),
    ], "State", readonly=True)

    lines = fields.One2Many(
        'hr.payslip.line', 'payslip', "Lines",
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])

    move = fields.Many2One('account.move', "Account Move", readonly=True)

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_currency():
        """
        პეისლიპის ვალუტა დეფოლტად – კომპანიის ვალუტა.
        """
        Company = Pool().get('company.company')
        companies = Company.search([], limit=1)
        if companies:
            return companies[0].currency.id
        return None

    @classmethod
    def __setup__(cls):
        super().__setup__()
        # თუ ჯერ არ არსებობს, შევქმნათ ცარიელი სტრუქტურები
        if not hasattr(cls, '_transitions'):
            cls._transitions = set()
        if not hasattr(cls, '_buttons'):
            cls._buttons = {}

        cls._transitions |= {
            ('draft', 'done'),
            ('draft', 'cancelled'),
            ('done', 'draft'),
        }
        cls._buttons.update({
            'compute': {
                'invisible': Eval('state') != 'draft',
                'depends': ['state'],
            },
            'complete': {
                'invisible': Eval('state') != 'draft',
                'depends': ['state'],
            },
            'reset_to_draft': {
                'invisible': Eval('state') != 'done',
                'depends': ['state'],
            },
            'cancel': {
                'invisible': Eval('state') == 'cancelled',
                'depends': ['state'],
            },
        })

    # --- Buttons ---

    @classmethod
    @ModelView.button
    def compute(cls, payslips):
        """
        ხელფასის დათვლა: სამუშაო დღეები, პენსია, საშემოსავლო, ხაზები.
        """
        PublicHoliday = Pool().get('ge.public_holiday')
        Line = Pool().get('hr.payslip.line')

        all_dates = [
            p.date_from for p in payslips if p.date_from
        ] + [
            p.date_to for p in payslips if p.date_to
        ]

        holiday_set = set()
        if all_dates:
            min_date = min(all_dates).replace(day=1)
            max_date = max(all_dates) + timedelta(days=32)
            try:
                holidays = PublicHoliday.search([
                    ('date', '>=', min_date),
                    ('date', '<=', max_date),
                    ('active', '=', True),
                ])
                holiday_set = {h.date for h in holidays}
            except Exception:
                holiday_set = set()

        for payslip in payslips:
            contract = payslip.contract
            if not contract or not payslip.date_from or not payslip.date_to:
                continue

            full_wage = Decimal(str(contract.wage or 0))

            # 1. თვის სამუშაო დღეები
            year = payslip.date_from.year
            month = payslip.date_from.month
            last_day_of_month = calendar.monthrange(year, month)[1]

            month_start = payslip.date_from.replace(day=1)
            month_end = payslip.date_from.replace(day=last_day_of_month)

            total_month_business_days = count_business_days(
                month_start, month_end, holiday_set)

            # 2. ნამუშევარი დღეები
            worked_business_days = count_business_days(
                payslip.date_from, payslip.date_to, holiday_set)

            cls.write([payslip], {
                'working_days': worked_business_days,
            })

            # თუ paid_days არ არის მითითებული → worked_business_days
            days_to_pay = payslip.paid_days \
                if payslip.paid_days is not None else worked_business_days

            # 3. Gross salary
            gross = Decimal('0.00')
            if total_month_business_days > 0 and days_to_pay > 0:
                daily_rate = full_wage / Decimal(total_month_business_days)
                gross = round_amount(daily_rate * Decimal(days_to_pay))
            elif days_to_pay > 0:
                gross = round_amount(full_wage)

            # 4. პენსია და საშემოსავლო
            pension_employee = Decimal('0.00')
            pension_employer = Decimal('0.00')

            if contract.pension_participant and gross:
                pension_employee = round_amount(gross * Decimal('0.02'))
                pension_employer = round_amount(gross * Decimal('0.02'))

            pension_total_deduction = pension_employee

            taxable_base = gross - pension_total_deduction
            income_tax = round_amount(taxable_base * Decimal('0.20')) \
                if taxable_base > 0 else Decimal('0.00')

            net = gross - pension_total_deduction - income_tax

            cls.write([payslip], {
                'paid_days': days_to_pay,
                'gross': gross,
                'pension_employee': pension_employee,
                'pension_employer': pension_employer,
                'income_tax': income_tax,
                'net': net,
            })

            # 5. ხაზების გენერაცია
            if payslip.lines:
                Line.delete(payslip.lines)

            lines_to_create = []

            if gross:
                desc = f"Basic Salary ({days_to_pay}/{total_month_business_days} days)"
                lines_to_create.append({
                    'payslip': payslip.id,
                    'name': desc,
                    'code': "BASIC",
                    'category': 'basic',
                    'quantity': Decimal(days_to_pay),
                    'rate': round_amount(
                        full_wage / Decimal(total_month_business_days)
                    ) if total_month_business_days else gross,
                    'amount': gross,
                })

            if pension_employee:
                lines_to_create.append({
                    'payslip': payslip.id,
                    'name': "Pension (Employee 2%)",
                    'code': "PEN_EMP",
                    'category': 'deduction',
                    'quantity': Decimal('1'),
                    'rate': pension_employee,
                    'amount': -pension_employee,
                })

            if pension_employer:
                lines_to_create.append({
                    'payslip': payslip.id,
                    'name': "Pension (Employer 2%)",
                    'code': "PEN_ER",
                    'category': 'other',
                    'quantity': Decimal('1'),
                    'rate': pension_employer,
                    'amount': pension_employer,
                })

            if income_tax:
                lines_to_create.append({
                    'payslip': payslip.id,
                    'name': "Income Tax 20%",
                    'code': "TAX",
                    'category': 'tax',
                    'quantity': Decimal('1'),
                    'rate': income_tax,
                    'amount': -income_tax,
                })

            if net:
                lines_to_create.append({
                    'payslip': payslip.id,
                    'name': "Net Salary",
                    'code': "NET",
                    'category': 'other',
                    'quantity': Decimal('1'),
                    'rate': net,
                    'amount': net,
                })

            if lines_to_create:
                Line.create(lines_to_create)

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def complete(cls, payslips):
        """
        პეისლიპის დასრულება და ბუღალტრული გატარების შექმნა.
        """
        for payslip in payslips:
            if not payslip.move:
                move = cls._create_move(payslip)
                if move:
                    cls.write([payslip], {'move': move.id})

    @classmethod
    def _create_move(cls, payslip):
        """
        გატარება:
        Dr Salary Expense
        Dr Employer Pension Expense
        Cr Pension Liability
        Cr Tax Liability
        Cr Net Salary Payable
        """
        contract = payslip.contract
        if not contract or not contract.journal:
            return None

        Move = Pool().get('account.move')
        Date = Pool().get('ir.date')

        move_lines = []

        # 1. DEBIT: Salary Expense (Gross)
        if contract.expense_account and payslip.gross:
            move_lines.append({
                'description': "Salary Expense",
                'account': contract.expense_account.id,
                'debit': payslip.gross,
                'credit': Decimal('0'),
            })

        # 2. DEBIT: Employer Pension Expense
        if payslip.pension_employer and payslip.pension_employer > 0:
            acc = contract.employer_pension_expense_account or \
                contract.expense_account
            if acc:
                move_lines.append({
                    'description': "Pension Expense (Employer 2%)",
                    'account': acc.id,
                    'debit': payslip.pension_employer,
                    'credit': Decimal('0'),
                })

        # 3. CREDIT: Pension Liability (Employee + Employer)
        total_pension = (payslip.pension_employee or Decimal('0')) + \
                        (payslip.pension_employer or Decimal('0'))
        if total_pension > 0 and contract.pension_account:
            move_lines.append({
                'description': "Pension Liability",
                'account': contract.pension_account.id,
                'debit': Decimal('0'),
                'credit': total_pension,
            })

        # 4. CREDIT: Tax Liability
        if payslip.income_tax and contract.tax_account:
            move_lines.append({
                'description': "Income Tax Liability",
                'account': contract.tax_account.id,
                'debit': Decimal('0'),
                'credit': payslip.income_tax,
            })

        # 5. CREDIT: Net Salary Payable
        if payslip.net and contract.payable_account:
            party = payslip.employee.party if payslip.employee else None
            move_lines.append({
                'description': "Net Salary Payable",
                'account': contract.payable_account.id,
                'debit': Decimal('0'),
                'credit': payslip.net,
                'party': party.id if party else None,
            })

        if not move_lines:
            return None

        values = {
            'journal': contract.journal.id,
            'date': payslip.date_to or Date.today(),
            'description': (
                f"Payroll {payslip.employee.rec_name} {payslip.date_from}"
            ),
            'lines': [('create', move_lines)],
        }

        move, = Move.create([values])
        return move

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def reset_to_draft(cls, payslips):
        """სტატუსის დაბრუნება draft-ზე."""
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('cancelled')
    def cancel(cls, payslips):
        """პეისლიპის გაუქმება (ამ ეტაპზე მხოლოდ სტატუსი)."""
        pass


class PayslipLine(ModelSQL, ModelView):
    "Payslip Line"
    __name__ = 'hr.payslip.line'

    payslip = fields.Many2One(
        'hr.payslip', "Payslip", required=True, ondelete='CASCADE')

    name = fields.Char("Description", required=True)
    code = fields.Char("Code")

    category = fields.Selection([
        ('basic', "Basic Salary"),
        ('allowance', "Allowance"),
        ('deduction', "Deduction"),
        ('tax', "Tax"),
        ('other', "Other"),
    ], "Category", required=True)

    quantity = fields.Numeric("Quantity", digits=(16, 2), required=True)
    rate = fields.Numeric("Rate", digits=(16, 2), required=True)
    amount = fields.Numeric("Amount", digits=(16, 2), required=True)
