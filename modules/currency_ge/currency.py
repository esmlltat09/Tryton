from decimal import Decimal, DivisionByZero, InvalidOperation
import datetime as dt
import json
import ssl
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from trytond.modules.currency.currency import CronFetchError
from trytond.pool import PoolMeta
from trytond.pyson import Eval, If
from trytond.model import fields

__all__ = ['Cron', 'Currency']
__metaclass__ = PoolMeta

# NBG JSON API:
# Example:
# https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json?date=YYYY-MM-DD
NBG_URL = (
    "https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json"
    "?date={date}"
)

REQUEST_TIMEOUT = 10  # seconds


def _fetch_nbg_raw(date):
    """Fetch raw JSON from NBG for a given date.

    Returns a Python object (dict/list) or raises CronFetchError.
    """
    if date is None:
        date = dt.date.today()
    date_str = date.strftime("%Y-%m-%d")

    url = NBG_URL.format(date=date_str)
    context = ssl.create_default_context()
    req = Request(url, headers={"User-Agent": "Tryton currency_ge"})

    try:
        with urlopen(req, context=context, timeout=REQUEST_TIMEOUT) as resp:
            data = resp.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        # დროებითი შეცდომა – CronFetchError-ით ვაბრუნებთ
        raise CronFetchError() from e

    try:
        data = json.loads(data)
    except ValueError as e:
        raise CronFetchError() from e

    return data


def _parse_nbg_rates(base_code, date):
    """Return mapping { 'USD': Decimal(foreign_per_1_GEL), ... }.

    NBG JSON:
        rate     = X GEL
        quantity = N units of foreign currency

    ოფიციალური მნიშვნელობა:
        N ერთ. FX = rate GEL
        1 FX      = rate / quantity GEL

    Tryton-ისთვის სტანდარტი:
        rate(field) = foreign_per_1_base
        1 GEL = value FX

    აქ ვთვლით:
        value = quantity / rate = რამდენი FX მოდის 1 GEL-ზე.
    """
    data = _fetch_nbg_raw(date)

    # Data structure: [ { "currencies": [ ... ] } ] or { "currencies": [ ... ] }
    if isinstance(data, list):
        if not data:
            raise CronFetchError()
        obj = data[0]
    else:
        obj = data

    currencies = obj.get("currencies")
    if not isinstance(currencies, list):
        raise CronFetchError()

    result = {}

    for item in currencies:
        code = item.get("code")
        if not code:
            continue

        try:
            rate = Decimal(str(item["rate"]))                 # GEL amount
            quantity = Decimal(str(item.get("quantity", 1)))  # FX units
        except (KeyError, ValueError, InvalidOperation):
            continue

        if rate <= 0 or quantity <= 0:
            continue

        # 1 GEL = value units of foreign currency (GEL → FX)
        value = (quantity / rate).quantize(Decimal('0.000000'))

        # Skip base currency itself
        if code == base_code:
            continue

        result[code] = value

    return result


class Cron(metaclass=PoolMeta):
    __name__ = "currency.cron"

    @classmethod
    def __setup__(cls):
        super().__setup__()
        entry = ("nbg", "National Bank of Georgia")
        if entry not in cls.source.selection:
            cls.source.selection.append(entry)

        # NBG-სთვის აუცილებელია, რომ საბაზო ვალუტა იყოს GEL
        cls.currency.domain = [
            cls.currency.domain or [],
            If(Eval('source') == 'nbg',
               ('code', '=', 'GEL'),
               ()),
        ]

    def fetch_nbg(self, date):
        """Fetch rates from NBG. Called when source == 'nbg'.

        აბრუნებს mapping-ს:
            1 GEL = rate FX
        """
        if self.currency.code != "GEL":
            raise CronFetchError("NBG source requires GEL as base currency")

        return _parse_nbg_rates(self.currency.code, date)


class Currency(metaclass=PoolMeta):
    __name__ = 'currency.currency'

    # დამატებითი Function ველი: 1 ერთეული უცხოური = X ლარი
    gel_per_unit = fields.Function(
        fields.Numeric('GEL per 1 Unit', digits=(16, 6)),
        'get_gel_per_unit'
    )

    @classmethod
    def get_gel_per_unit(cls, currencies, name):
        """Convert Tryton's rate (foreign per 1 GEL)
        into GEL per 1 foreign unit: 1 / rate.

        თუ current_rate = 0.369208 (1 GEL = 0.369208 USD),
        აქ მივიღებთ: 1 / 0.369208 ≈ 2.7083 GEL per 1 USD.
        """
        res = {}
        for cur in currencies:
            # ვცადოთ ჯერ 'rate', მერე 'current_rate'
            rate = getattr(cur, 'rate', None)
            if rate is None:
                rate = getattr(cur, 'current_rate', None)

            try:
                if rate:
                    value = (Decimal('1') / rate).quantize(
                        Decimal('0.000001')
                    )
                    res[cur.id] = value
                else:
                    res[cur.id] = None
            except (DivisionByZero, InvalidOperation):
                res[cur.id] = None
        return res
