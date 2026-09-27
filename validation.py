"""Κοινή επικύρωση στοιχείων βιβλίων."""

from constants import READ, UNREAD


def normalize_status(value, allow_empty=True):
    value = value.strip().casefold()
    if value == "μη διαβασμένο" or (not value and allow_empty):
        return UNREAD
    if value not in (READ, UNREAD):
        raise ValueError("Δεκτές καταστάσεις: διαβασμένο ή αδιάβαστο.")
    return value


def parse_year(value):
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 9999:
        raise ValueError("Το έτος πρέπει να είναι ακέραιος από 1 έως 9999.")
    return int(value)


def prompt_year(prompt):
    while True:
        try:
            return parse_year(input(prompt))
        except ValueError as exc:
            print(f"{exc}")


def validate_isbn(value, allow_empty=False):
    """Επιστρέφει ISBN χωρίς κενά/παύλες ή εγείρει ValueError.

    Ελέγχει μορφή και checksum, όχι αν το ISBN έχει εκδοθεί πραγματικά.
    Το None επιτρέπεται μόνο για καταχώρηση χωρίς ISBN.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        if allow_empty:
            return None
        raise ValueError("Δώσε ISBN-10 ή ISBN-13.")
    if not isinstance(value, str):
        raise ValueError("Το ISBN πρέπει να είναι κείμενο, ώστε να διατηρούνται τα αρχικά μηδενικά.")
    isbn = ''.join(c for c in value if not c.isspace() and c != '-').upper()
    if len(isbn) == 10:
        if not (isbn[:9].isascii() and isbn[:9].isdigit()
                and isbn[-1] in '0123456789X'):
            raise ValueError("Το ISBN-10 χρειάζεται 9 ψηφία και ένα ψηφίο ή X στο τέλος.")
        digits = [10 if c == 'X' else int(c) for c in isbn]
        valid = sum((10 - i) * digit for i, digit in enumerate(digits)) % 11 == 0
    elif len(isbn) == 13:
        if not (isbn.isascii() and isbn.isdigit() and isbn.startswith(('978', '979'))):
            raise ValueError("Το ISBN-13 χρειάζεται 13 ψηφία και πρόθεμα 978 ή 979.")
        valid = sum(int(c) * (1 if i % 2 == 0 else 3)
                    for i, c in enumerate(isbn)) % 10 == 0
    else:
        raise ValueError("Το ISBN πρέπει να έχει 10 ή 13 χαρακτήρες, χωρίς τα κενά και τις παύλες.")
    if not valid:
        raise ValueError("Μη έγκυρο ISBN: λάθος ψηφίο επαλήθευσης.")
    return isbn


def isbn_key(value):
    """Κοινό ISBN-13 για σύγκριση ισοδύναμων ISBN-10 και ISBN-13."""
    isbn = validate_isbn(value, allow_empty=True)
    if isbn is None or len(isbn) == 13:
        return isbn
    prefix = "978" + isbn[:9]
    checksum = (-sum(int(c) * (1 if i % 2 == 0 else 3)
                     for i, c in enumerate(prefix))) % 10
    return prefix + str(checksum)
