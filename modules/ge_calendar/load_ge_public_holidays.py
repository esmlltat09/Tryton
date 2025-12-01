from datetime import date, timedelta
from trytond.config import config
from trytond.pool import Pool
from trytond.transaction import Transaction

# Tryton-ის კონფიგურაციის ჩატვირთვა
config.update_etc('/etc/trytond.conf')

# ამ ბაზაში უნდა შევიყვანოთ დღესასწაულები
DB_NAME = 'tr_fresh'


def orthodox_easter(year: int) -> date:
    """
    მართლმადიდებელი აღდგომის თარიღი (გრიგორიანულ კალენდარში).
    """
    a = year % 4
    b = year % 7
    c = year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = ((d + e + 114) % 31) + 1

    julian_easter = date(year, month, day)
    return julian_easter + timedelta(days=13)


def main():
    # ვიწყებთ ტრანზაქციას
    with Transaction().start(DB_NAME, 0) as transaction:
        pool = Pool()
        pool.init()

        Country = pool.get('country.country')
        PublicHoliday = pool.get('ge.public_holiday')

        # --- 1. ვპოულობთ ან ვქმნით საქართველოს ---
        countries = Country.search([('code', '=', 'GE')])
        if not countries:
            print("Country 'GE' not found. Creating Georgia...")
            georgia = Country(name='Georgia', code='GE')
            georgia.save()
        else:
            georgia = countries[0]

        # --- 2. ფიქსირებული დღესასწაულები ---
        fixed_holidays = [
            (1, 1,  "ახალი წლის დღე (1 იანვარი)"),
            (1, 2,  "ახალი წლის დღე (2 იანვარი)"),
            (1, 7,  "შობა ქრისტესი"),
            (1, 19, "ნათლისღება"),
            (3, 3,  "დედის დღე"),
            (3, 8,  "ქალთა საერთაშორისო დღე"),
            (4, 9,  "9 აპრილი"),
            (5, 9,  "ფაშიზმზე გამარჯვების დღე"),
            (5, 12, "ანდრია მოციქულის ხსენება / საქართველოს წილხვდომილობა"),
            (5, 26, "დამოუკიდებლობის დღე"),
            (8, 28, "მარიამობა"),
            (10, 14, "მცხეთობა"),
            (11, 23, "გიორგობა"),
        ]

        YEARS = range(2025, 2031)
        created = 0
        skipped = 0

        for year in YEARS:
            # ა) ფიქსირებული დღეები
            for month, day, name in fixed_holidays:
                d = date(year, month, day)
                
                # შემოწმება: არსებობს თუ არა?
                existing = PublicHoliday.search([
                    ('country', '=', georgia.id),
                    ('date', '=', d),
                ])
                if existing:
                    skipped += 1
                    continue

                holiday = PublicHoliday(
                    name=name,
                    date=d,
                    country=georgia,
                    active=True,
                )
                holiday.save()
                created += 1

            # ბ) სააღდგომო მოძრავი დღეები
            easter_sunday = orthodox_easter(year)
            moving_holidays = [
                (easter_sunday - timedelta(days=2), "დიდი პარასკევი"),
                (easter_sunday - timedelta(days=1), "დიდი შაბათი"),
                (easter_sunday, "აღდგომა"),
                (easter_sunday + timedelta(days=1),
                 "აღდგომის მეორე დღე (მიცვალებულთა მოხსენიება)"),
            ]

            for d, name in moving_holidays:
                existing = PublicHoliday.search([
                    ('country', '=', georgia.id),
                    ('date', '=', d),
                ])
                if existing:
                    skipped += 1
                    continue

                holiday = PublicHoliday(
                    name=name,
                    date=d,
                    country=georgia,
                    active=True,
                )
                holiday.save()
                created += 1

        transaction.commit()
        print(f"Success! Created {created} holidays. Skipped {skipped} existing.")


if __name__ == '__main__':
    main()