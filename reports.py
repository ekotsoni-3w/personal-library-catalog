"""Εμφάνιση βιβλίων, αναζητήσεις, στατιστικά και γραφήματα."""

from constants import READ, UNREAD

import database


def show_books():
    rows = database.get_books()

    if not rows:
        print("Δεν υπάρχουν βιβλία στη βάση.\n")
        return

    print("\nΛίστα βιβλίων:")
    for row in rows:
        title, author, genre, year, isbn, status, notes = row
        print(f"- {title} ({year}) | {author} | Είδος: {genre} | ISBN: {isbn}")
        print(f"  Κατάσταση: {status or '—'}")
        if notes:
            print(f"  Σημειώσεις: {notes}")
        print()


def show_books_by_status():
    print("\nΤι θέλεις να δεις;")
    print("1 - Διαβασμένα βιβλία")
    print("2 - Αδιάβαστα βιβλία")
    choice = input("> ").strip()

    if choice == "1":
        status = READ
    elif choice == "2":
        status = UNREAD
    else:
        print("Μη έγκυρη επιλογή.")
        return

    rows = database.get_books_by_status(status)

    if not rows:
        print(f"\nΔεν υπάρχουν {status} βιβλία στη βάση.\n")
        return

    print(f"\nΛίστα {status} βιβλίων:")
    for row in rows:
        title, author, genre, year, isbn, status, notes = row
        print(f"- {title} ({year}) | {author} | Είδος: {genre} | ISBN: {isbn}")
        if notes:
            print(f"  Σημειώσεις: {notes}")
        print()


def search_books():
    print("\nΑναζήτηση βιβλίου:")
    print("1 - Με βάση τον τίτλο")
    print("2 - Με βάση τον συγγραφέα")
    choice = input("> ").strip()

    if choice == "1":
        keyword = input("Πληκτρολόγησε λέξη-κλειδί από τον τίτλο: ").strip()
        rows = database.find_books_by_title(keyword)
    elif choice == "2":
        keyword = input("Πληκτρολόγησε όνομα συγγραφέα: ").strip()
        rows = database.find_books_by_author(keyword)
    else:
        print("Μη έγκυρη επιλογή.")
        return

    if not rows:
        print("\nΔεν βρέθηκαν βιβλία.\n")
        return

    print("\nΑποτελέσματα αναζήτησης:")
    for row in rows:
        title, author, genre, year, isbn, status, notes = row
        print(f"- {title} ({year}) | {author} | Είδος: {genre} | ISBN: {isbn}")
        print(f"  Κατάσταση: {status or '—'}")
        if notes:
            print(f"  Σημειώσεις: {notes}")
        print()


def show_books_by_author():
    author_name = input("\nΠληκτρολόγησε το όνομα του συγγραφέα: ").strip()

    # Αναζήτηση βιβλίων που ανήκουν σε αυτόν τον συγγραφέα (όλα, όχι μόνο διαβασμένα)
    rows = database.get_books_by_author(author_name)

    if not rows:
        print(f"\nΔεν βρέθηκαν βιβλία για τον συγγραφέα '{author_name}'.\n")
        return

    print(f"\nΒιβλία του συγγραφέα '{author_name}':")
    for row in rows:
        title, genre, year, isbn, status, notes = row
        print(f"- {title} ({year}) | Είδος: {genre or '—'} | ISBN: {isbn}")
        print(f"  Κατάσταση: {status or '—'}")
        if notes:
            print(f"  Σημειώσεις: {notes}")
        print()


def stats_by_year():
    rows = database.get_year_counts()

    if not rows:
        print("\nΔεν υπάρχουν διαβασμένα βιβλία.\n")
        return

    print("\nΣτατιστικά διαβασμένων βιβλίων ανά έτος ανάγνωσης:")
    for read_year, count in rows:
        print(f"- {read_year}: {count} βιβλία")


def plot_books_by_year():
    data = database.get_year_counts()

    if not data:
        print("Δεν υπάρχουν διαβασμένα βιβλία για να εμφανιστούν σε γράφημα.")
        return

    years = [str(row[0]) for row in data]
    counts = [row[1] for row in data]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(10,5))
    plt.bar(years, counts, color='skyblue')
    plt.title("Διαβασμένα βιβλία ανά έτος")
    plt.xlabel("Έτος ανάγνωσης")
    plt.ylabel("Αριθμός βιβλίων")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def stats_by_author():
    rows = database.get_author_counts()

    if not rows:
        print("\nΔεν υπάρχουν διαβασμένα βιβλία.\n")
        return

    print("\nΣτατιστικά διαβασμένων βιβλίων ανά συγγραφέα:")
    for author, count in rows:
        print(f"- {author}: {count} βιβλία")


def plot_books_by_author():
    data = database.get_author_counts()

    if not data:
        print("Δεν υπάρχουν διαβασμένα βιβλία για να εμφανιστούν σε γράφημα.")
        return

    authors = [row[0] or "Άγνωστος" for row in data]
    counts = [row[1] for row in data]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(12,6))
    plt.barh(authors, counts, color='lightgreen')
    plt.title("Διαβασμένα βιβλία ανά συγγραφέα")
    plt.xlabel("Αριθμός βιβλίων")
    plt.ylabel("Συγγραφέας")
    plt.tight_layout()
    plt.show()
