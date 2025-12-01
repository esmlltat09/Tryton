from trytond.model import ModelSQL, ModelView, fields


class PublicHoliday(ModelSQL, ModelView):
    "Public Holiday"
    __name__ = 'ge.public_holiday'

    name = fields.Char("Name", required=True)
    date = fields.Date("Date", required=True)
    country = fields.Many2One(
        'country.country', "Country", required=True)
    active = fields.Boolean("Active")

    _sql_constraints = [
        ('date_country_uniq', 'UNIQUE(date, country)',
         'A public holiday already exists for this date and country.'),
    ]

    @staticmethod
    def default_active():
        return True
