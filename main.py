"""Σημείο εκκίνησης και κύριο μενού της εφαρμογής."""

import api
import book_actions
import database
import reports
from validation import validate_isbn


def main():
    database.init_db()
    while True:
        print("\nΕπιλογές:")
        print("1 - Πρόσθεσε βιβλίο με ISBN")
        print("2 - Δες όλα τα βιβλία")
        print("3 - Ενημέρωσε κατάσταση βιβλίου (διαβασμένο/αδιάβαστο)")
        print("4 - Δες διαβασμένα ή αδιάβαστα βιβλία")
        print("5 - Αναζήτηση βιβλίου")
        print("6 - Δες όλα τα βιβλία ενός συγγραφέα")
        print("7 - Στατιστικά ανά έτος")
        print("8 - Στατιστικά ανά συγγραφέα")
        print("9 - Έξοδος")

        choice = input("> ").strip()

        if choice == "1":
            try:
                isbn = validate_isbn(input("Δώσε ISBN: "))
                database.check_duplicate(isbn=isbn)
            except ValueError as exc:
                print(exc)
                continue
            book_info = api.get_book_info_by_isbn(isbn)
            if book_info:
                try:
                    book_actions.add_book(book_info["title"], book_info["authors"], book_info["genres"], book_info["year"], isbn)
                except ValueError as exc:
                    print(f"{exc}")
            else:
                print("Δεν βρέθηκαν αποτελέσματα για αυτό το ISBN.")
                manual_add = input("Θες να το προσθέσεις χειροκίνητα; (ν/ο): ").lower()
                if manual_add == "ν":
                    try:
                        book_actions.manual_entry(isbn)
                    except ValueError as exc:
                        print(f"{exc}")

        elif choice == "2":
            reports.show_books()

        elif choice == "3":
            book_actions.update_book_status()

        elif choice == "4":
            reports.show_books_by_status()

        elif choice == "5":
            reports.search_books()
        
        elif choice == "6":
            reports.show_books_by_author()

        elif choice == "7":
            reports.stats_by_year()
            reports.plot_books_by_year()

        elif choice == "8":
            reports.stats_by_author()
            reports.plot_books_by_author()

        elif choice == "9":
            print("Έξοδος από το πρόγραμμα.")
            break

        else:
            print("Μη έγκυρη επιλογή. Προσπάθησε ξανά.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nΈξοδος από το πρόγραμμα.")
