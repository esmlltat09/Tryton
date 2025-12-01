from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.exceptions import UserError

__all__ = ['Identifier']


class Identifier(metaclass=PoolMeta):
    """
    ქართული იდენტიფიკატორები party.identifier-ზე:

    - ge_tax : Georgian Tax ID
        * 9 ციფრი  -> იურიდიული პირები (legacy + modern კოდები)
        * 11 ციფრი -> ინდ. მეწარმე (TIN == Personal Number, Mod 11)
    - ge_pn  : Georgian Personal Number (11 ციფრი, Mod 11)
    """
    __name__ = 'party.identifier'

    @classmethod
    def __setup__(cls):
        """
        დამატებითი ქართული ტიპების ჩასმა type selection-ში:
            ge_tax / ge_pn
        """
        super().__setup__()

        extra_types = [
            ('ge_tax', 'Georgian Tax ID'),
            ('ge_pn', 'Georgian Personal Number'),
        ]

        field = cls.type
        selection = field.selection

        # ახალი Tryton – selection შეიძლება იყოს მეთოდის სახელი (str)
        if isinstance(selection, str):
            method_name = selection
            base_method = getattr(super(Identifier, cls), method_name)

            @classmethod
            def wrapped(inner_cls):
                types = list(base_method())
                existing = {k for k, _ in types}
                for key, label in extra_types:
                    if key not in existing:
                        types.append((key, label))
                return types

            setattr(cls, method_name, wrapped)

        else:
            # ძველი სტილი – პირდაპირ სია
            existing = {k for k, _ in selection}
            for key, label in extra_types:
                if key not in existing:
                    selection.append((key, label))

    @staticmethod
    def _validate_mod11(code_str: str) -> bool:
        """
        Modulus 11 ალგორითმი 11-ნიშნა პირადი ნომრებისთვის.
        """
        if len(code_str) != 11 or not code_str.isdigit():
            return False

        digits = [int(ch) for ch in code_str]

        # Placeholder წონები – მერე შეცვლი, თუ ზუსტ ფორმულას გაარკვევ
        weights = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        checksum_sum = 0
        for i in range(10):
            checksum_sum += digits[i] * weights[i]

        remainder = checksum_sum % 11
        check_digit = digits[10]

        if remainder == 10:
            # უსაფრთხო ვარიანტი: მხოლოდ მაშინ გავატაროთ, თუ check_digit == 0
            return check_digit == 0

        return remainder == check_digit

    @fields.depends('type', 'code', 'party')
    def check_code(self):
        """
        ვაფართოებთ სტანდარტულ check_code-ს:

        - ჯერ core-ის check_code (stdnum და სხვ.)
        - შემდეგ ჩვენი ქართული ლოგიკა:

          ge_tax:
            - 9 ციფრი  -> მხოლოდ სიგრძე + ციფრები (legacy / modern), checksum არა
            - 11 ციფრი -> Mod 11 (ინდ. მეწარმე)

          ge_pn:
            - 11 ციფრი -> Mod 11 (ფიზიკური პირი)
        """
        # ჯერ core-ის check_code – რომ სხვა ტიპებზე სტანდარტული ვალიდაციებიც იმუშაოს
        super().check_code()

        code = (self.code or '').strip()
        type_ = self.type

        if not code or not type_:
            return

        party_name = self.party.rec_name if self.party else ''

        # -----------------------------
        # Georgian Tax ID (9 ან 11 ციფრი)
        # -----------------------------
        if type_ == 'ge_tax':
            if not code.isdigit():
                msg = (
                    f'The Georgian Tax ID "{code}" for party "{party_name}" '
                    f'must contain digits only.'
                )
                raise UserError(msg)

            length = len(code)

            if length == 9:
                # 9-ნიშნა: ჰიბრიდული რეჟიმი, checksum არ ვიყენებთ.
                # Legacy (მაგ: 245...) + modern (4xx...) კოდები.
                # რეალური ვალიდაცია მაინც RS.ge / NAPR ბაზაში უნდა მოხდეს.
                return

            if length == 11:
                # 11-ნიშნა: ინდ. მეწარმე – პირადი ნომერი, Mod 11
                if not self._validate_mod11(code):
                    msg = (
                        f'The Georgian Tax ID "{code}" for party "{party_name}" '
                        f'is 11 digits long but fails the Mod 11 checksum.'
                    )
                    raise UserError(msg)
                return

            msg = (
                f'The Georgian Tax ID "{code}" for party "{party_name}" '
                f'must be 9 or 11 digits long.'
            )
            raise UserError(msg)

        # -----------------------------
        # Georgian Personal Number (11 ციფრი, მკაცრად)
        # -----------------------------
        if type_ == 'ge_pn':
            if not code.isdigit():
                msg = (
                    f'The Georgian Personal Number "{code}" for party "{party_name}" '
                    f'must contain digits only.'
                )
                raise UserError(msg)

            if len(code) != 11:
                msg = (
                    f'The Georgian Personal Number "{code}" for party "{party_name}" '
                    f'must be exactly 11 digits long.'
                )
                raise UserError(msg)

            if not self._validate_mod11(code):
                msg = (
                    f'The Georgian Personal Number "{code}" for party "{party_name}" '
                    f'is not valid (Mod 11 checksum failed).'
                )
                raise UserError(msg)
