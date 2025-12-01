from trytond.pool import Pool
from . import models


def register():
    Pool.register(
        models.PublicHoliday,
        module='ge_calendar', type_='model',
    )
