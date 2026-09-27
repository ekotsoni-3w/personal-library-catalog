import database
from validation import prompt_year

def batch_update_read_year():
    books = database.get_books_missing_read_year()

    if not books:
        print("Δεν υπάρχουν βιβλία που χρειάζονται ενημέρωση read_year.\n")
        return

    print("\nΒιβλία χωρίς έτος ανάγνωσης:")
    for book in books:
        print(f"{book[0]}. {book[1]} — Κατάσταση: {book[2] or '—'}")

    print("\nΜπορείς να προσθέσεις το έτος ανάγνωσης για κάθε βιβλίο ή να αφήσεις κενό αν δεν θες.\n")

    for book in books:
        read_year = prompt_year(f"Έτος που διάβασες '{book[1]}' (ID {book[0]}): ")
        if read_year is not None:
            database.update_read_year(book[0], read_year)
            print(f"Ενημερώθηκε το έτος ανάγνωσης σε {read_year}")
        else:
            print("— Δεν αλλάζει τίποτα για αυτό το βιβλίο.")

    print("\nΗ ενημέρωση ολοκληρώθηκε!")

if __name__ == "__main__":
    database.init_db()
    batch_update_read_year()
