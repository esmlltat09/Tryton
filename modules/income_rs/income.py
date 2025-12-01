from decimal import Decimal
from trytond.model import ModelSQL, ModelView, fields

__all__ = ['IncomeDeclaration', 'IncomeDeclarationLine']


class IncomeDeclaration(ModelSQL, ModelView):
    "RS.GE Source Withholding Income Declaration"
    __name__ = 'ge.income.declaration'

    company = fields.Many2One('company.company', "Company", required=True)
    period = fields.Many2One('account.period', "Period", required=True)

    state = fields.Selection([
        ('draft', "Draft"),
        ('computed', "Computed"),
        ('sent', "Sent to RS"),
    ], "State", required=True)

    lines = fields.One2Many(
        'ge.income.declaration.line', 'declaration', "Lines")

    # Readonly დავამატეთ, რომ მომხმარებელმა ხელით არ შეცვალოს ჯამები
    total_amount = fields.Numeric(
        "სულ განაცემი თანხა", digits=(16, 2), readonly=True)
    total_tax = fields.Numeric(
        "სულ გადასახადი", digits=(16, 2), readonly=True)

    rs_id = fields.Char("RS Declaration ID", readonly=True)
    rs_status = fields.Char("RS Status", readonly=True)

    @staticmethod
    def default_state():
        return 'draft'

    @fields.depends('lines')
    def on_change_lines(self):
        total_amount = Decimal('0.00')
        total_tax = Decimal('0.00')
        for line in (self.lines or []):
            if line.amount:
                total_amount += line.amount
            if line.tax_amount:
                total_tax += line.tax_amount
        self.total_amount = total_amount
        self.total_tax = total_tax

    @classmethod
    @ModelView.button
    def compute(cls, declarations):
        for decl in declarations:
            # თითო ხაზზე მივითვლით გადასახადს
            for line in decl.lines:
                line.calculate_tax()
                line.save() # ხაზს ვინახავთ
            
            # გადავთვლით ჯამებს
            decl.on_change_lines()
            decl.state = 'computed'
            decl.save()

    @classmethod
    @ModelView.button
    def send_rs(cls, declarations):
        for decl in declarations:
            # აქ იქნება RS-ზე XML ატვირთვის ლოგიკა
            decl.state = 'sent'
            decl.save()


class IncomeDeclarationLine(ModelSQL, ModelView):
    "RS.GE Source Withholding Line"
    __name__ = 'ge.income.declaration.line'

    declaration = fields.Many2One(
        'ge.income.declaration', "Declaration",
        required=True, ondelete='CASCADE')

    tin = fields.Char("პ/ნ ან საიდენტიფიკაციო", size=11, required=True)
    first_name = fields.Char("სახელი / სამართლებრივი ფორმა", required=True)
    last_name = fields.Char("გვარი / დასახელება")
    address = fields.Char("მისამართი")

    residency_code = fields.Char("რეზიდენტობა (კოდი)", size=3)

    recipient_category = fields.Char("პირთა კატეგორია", size=2)
    payment_type = fields.Char("განაცემის სახე", size=2)

    amount = fields.Numeric(
        "განაცემი თანხა", digits=(16, 2), required=True)
    other_relief = fields.Numeric(
        "სხვა შეღავათები", digits=(16, 2))

    payment_date = fields.Date("გაცემის თარიღი", required=True)

    tax_rate = fields.Numeric(
        "განაკვეთი (%)", digits=(16, 2), required=True)

    treaty_exempt_tax = fields.Numeric(
        "ხელშეკრულებით გათავისუფლებული", digits=(16, 2))
    foreign_tax_credit = fields.Numeric(
        "უცხოეთში გადახდილი ჩათვლა", digits=(16, 2))

    tax_amount = fields.Numeric(
        "დაკავებული საშემოსავლო", digits=(16, 2))

    @staticmethod
    def default_residency_code():
        # 268 - საქართველო
        return '268'

    @staticmethod
    def default_tax_rate():
        return Decimal('20.00')

    @fields.depends(
        'amount', 'other_relief', 'tax_rate',
        'treaty_exempt_tax', 'foreign_tax_credit')
    def on_change_with_tax_amount(self, name=None):
        amount = self.amount or Decimal('0.00')
        relief = self.other_relief or Decimal('0.00')
        rate = self.tax_rate or Decimal('0.00')
        treaty = self.treaty_exempt_tax or Decimal('0.00')
        foreign = self.foreign_tax_credit or Decimal('0.00')

        taxable_base = amount - relief
        if taxable_base < 0:
            taxable_base = Decimal('0.00')

        calculated_tax = (taxable_base * rate) / Decimal('100.00')
        final_tax = calculated_tax - treaty - foreign

        if final_tax < 0:
            final_tax = Decimal('0.00')

        return final_tax

    def calculate_tax(self):
        self.tax_amount = self.on_change_with_tax_amount()