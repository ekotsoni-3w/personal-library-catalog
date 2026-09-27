"""Διαδραστική καταχώρηση και ενημέρωση βιβλίων."""

from constants import READ

import database
from validation import validate_isbn, normalize_status, parse_year, prompt_year


def add_book(title, author, genre, year, isbn, status=None, notes=None, read_year=None):
    title, author, genre = title.strip(), author.strip(), genre.strip()
    if not title or not author or not genre:
        raise ValueError("Ο τίτλος, ο συγγραφέας και το είδος είναι υποχρεωτικά.")
    isbn = validate_isbn(isbn, allow_empty=True)
    year = parse_year(year)
    database.check_duplicate(title, author, isbn)
    if status is None:
        status = input("Κατάσταση (διαβασμένο/αδιάβαστο, κενό = αδιάβαστο): ")
    status = normalize_status(status)
    if notes is None:
        notes = input("Σημειώσεις (προαιρετικές): ").strip()
    if status == READ:
        read_year = prompt_year("Έτος ανάγνωσης (προαιρετικό): ") if read_year is None else parse_year(read_year)
    else:
        read_year = None

    database.add_book(title, author, genre, year, isbn, status, notes, read_year)
    print(f"Το βιβλίο '{title}' προστέθηκε με επιτυχία!\n")


def manual_entry(isbn=None):
    print("\nΚαταχώρηση βιβλίου χειροκίνητα:")
    title = input("Τίτλος: ")
    author = input("Συγγραφέας: ")
    genre = input("Είδος: ")
    year = prompt_year("Έτος έκδοσης (προαιρετικό): ")
    add_book(title, author, genre, year, isbn)


def update_book_status():
    books = database.get_book_statuses()

    if not books:
        print("Δεν υπάρχουν βιβλία στη βάση.\n")
        return

    for book in books:
        print(f"{book[0]}. {book[1]} — Κατάσταση: {book[2] or '—'}")

    try:
        book_id = int(input("\nID βιβλίου για ενημέρωση: "))
    except ValueError:
        print("Πρέπει να δώσεις αριθμό.")
        return

    result = database.get_book_title(book_id)
    if not result:
        print("Δεν βρέθηκε βιβλίο με αυτό το ID.")
        return

    try:
        new_status = normalize_status(input("Νέα κατάσταση (διαβασμένο / αδιάβαστο): "), allow_empty=False)
    except ValueError:
        print("Δεκτές τιμές: 'διαβασμένο' ή 'αδιάβαστο'.")
        return

    # Αν είναι διαβασμένο, ρώτησε για read_year
    read_year = None
    if new_status == READ:
        read_year = prompt_year("Έτος που διάβασες το βιβλίο (προαιρετικό): ")

    database.update_book_status(book_id, new_status, read_year)

    print(f"Ενημερώθηκε η κατάσταση του '{result[0]}' σε '{new_status}'.\n")
