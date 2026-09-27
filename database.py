"""
Πρόσβαση στη βάση: αρχικοποίηση, αποθήκευση και ερωτήματα.

"""

from constants import READ, UNREAD
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

from validation import isbn_key, validate_isbn, normalize_status, parse_year

DB_NAME = Path(__file__).resolve().parent / "books.db"

def column_exists(cursor, table, column):
    """Ελέγχει αν υπάρχει συγκεκριμένη στήλη σε πίνακα."""
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def add_column_if_missing(cursor, table, column, column_type):
    """Προσθέτει στήλη αν δεν υπάρχει ήδη."""
    if not column_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type};")
        print(f"Προστέθηκε στήλη '{column}' στον πίνακα '{table}'")

def init_db(db_name=None):
    with connection(db_name) as conn:
        cursor = conn.cursor()

        # --- Δημιουργία πινάκων αν δεν υπάρχουν ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author_id INTEGER,
            genre_id INTEGER,
            year INTEGER,
            FOREIGN KEY (author_id) REFERENCES authors(id),
            FOREIGN KEY (genre_id) REFERENCES genres(id)
        )
        """)

        # --- Έλεγχος/προσθήκη νέων στηλών ---
        add_column_if_missing(cursor, "books", "isbn", "TEXT")
        add_column_if_missing(cursor, "books", "status", "TEXT")
        add_column_if_missing(cursor, "books", "notes", "TEXT")

        add_column_if_missing(cursor, "books", "read_year", "INTEGER")

    print("Η βάση δεδομένων ενημερώθηκε επιτυχώς!")


@contextmanager
def connection(db_name=None):
    """Κλείνει πάντα τη σύνδεση και αναιρεί αποτυχημένες εγγραφές."""
    conn = sqlite3.connect(DB_NAME if db_name is None else db_name)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def fetch_all(query, parameters=()):
    with connection() as conn:
        return conn.execute(query, parameters).fetchall()


def add_author(name):
    with connection() as conn:
        conn.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (name,))
        return conn.execute("SELECT id FROM authors WHERE name = ?", (name,)).fetchone()[0]


def add_genre(name):
    with connection() as conn:
        conn.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (name,))
        return conn.execute("SELECT id FROM genres WHERE name = ?", (name,)).fetchone()[0]


class DuplicateBookError(ValueError):
    def __init__(self, book_id, title):
        self.book_id = book_id
        super().__init__(f"Το βιβλίο υπάρχει ήδη στη βάση: '{title}' (ID {book_id}).")


def _text_key(value):
    return ' '.join(unicodedata.normalize('NFC', value or '').casefold().split())


def _check_duplicate(conn, title, author, isbn):
    key = isbn_key(isbn)
    rows = conn.execute("""
        SELECT b.id, b.title, a.name, b.isbn
        FROM books b LEFT JOIN authors a ON a.id = b.author_id
        ORDER BY b.id
    """)
    for book_id, old_title, old_author, old_isbn in rows:
        try:
            old_key = isbn_key(old_isbn)
        except ValueError:
            # Παλιές εγγραφές μπορεί να έχουν μη έγκυρο ISBN.
            old_key = None
        same_isbn = key is not None and key == old_key
        same_text = ((key is None or old_key is None)
                     and _text_key(title) == _text_key(old_title)
                     and _text_key(author) == _text_key(old_author))
        if same_isbn or same_text:
            raise DuplicateBookError(book_id, old_title)


def check_duplicate(title=None, author=None, isbn=None):
    """Πρώιμος έλεγχος για τη διεπαφή· επαναλαμβάνεται κατά την εγγραφή."""
    with connection() as conn:
        _check_duplicate(conn, title, author, isbn)


def add_book(title, author, genre, year, isbn, status=UNREAD, notes="", read_year=None):
    title, author, genre = title.strip(), author.strip(), genre.strip()
    if not title or not author or not genre:
        raise ValueError("Ο τίτλος, ο συγγραφέας και το είδος είναι υποχρεωτικά.")
    isbn = validate_isbn(isbn, allow_empty=True)
    year = parse_year(year)
    status = normalize_status(status)
    read_year = parse_year(read_year) if status == READ else None

    with connection() as conn:
        # Κλειδώνει τις εγγραφές πριν από τον έλεγχο ώστε δύο εκτελέσεις
        # να μην μπορούν να προσθέσουν ταυτόχρονα το ίδιο βιβλίο.
        conn.execute("BEGIN IMMEDIATE")
        _check_duplicate(conn, title, author, isbn)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (author,))
        author_id = cursor.execute("SELECT id FROM authors WHERE name = ?", (author,)).fetchone()[0]
        cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre,))
        genre_id = cursor.execute("SELECT id FROM genres WHERE name = ?", (genre,)).fetchone()[0]
        cursor.execute("""
            INSERT INTO books (title, author_id, genre_id, year, isbn, status, notes, read_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, author_id, genre_id, year, isbn, status, notes, read_year))
        return cursor.lastrowid


def get_books():
    return fetch_all("""
        SELECT b.title, a.name, g.name, b.year, b.isbn, b.status, b.notes
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.id
        LEFT JOIN genres g ON b.genre_id = g.id
        ORDER BY a.name
    """)


def get_books_by_status(status):
    return fetch_all("""
        SELECT b.title, a.name, g.name, b.year, b.isbn, b.status, b.notes
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.id
        LEFT JOIN genres g ON b.genre_id = g.id
        WHERE b.status = ?
        ORDER BY a.name
    """, (status,))


def find_books_by_title(keyword):
    return fetch_all("""
        SELECT b.title, a.name, g.name, b.year, b.isbn, b.status, b.notes
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.id
        LEFT JOIN genres g ON b.genre_id = g.id
        WHERE b.title LIKE ?
        ORDER BY b.title
    """, (f"%{keyword}%",))


def find_books_by_author(keyword):
    return fetch_all("""
        SELECT b.title, a.name, g.name, b.year, b.isbn, b.status, b.notes
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.id
        LEFT JOIN genres g ON b.genre_id = g.id
        WHERE a.name LIKE ?
        ORDER BY b.title
    """, (f"%{keyword}%",))


def get_books_by_author(author_name):
    return fetch_all("""
        SELECT b.title, g.name, b.year, b.isbn, b.status, b.notes
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.id
        LEFT JOIN genres g ON b.genre_id = g.id
        WHERE a.name LIKE ?
        ORDER BY b.year
    """, (f"%{author_name}%",))


def get_year_counts():
    return fetch_all("""
        SELECT read_year, COUNT(*) 
        FROM books
        WHERE status = ? AND read_year IS NOT NULL
        GROUP BY read_year
        ORDER BY read_year
    """, (READ,))


def get_author_counts():
    return fetch_all("""
        SELECT a.name, COUNT(*)
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.id
        WHERE b.status = ?
        GROUP BY a.name
        ORDER BY COUNT(*) DESC
    """, (READ,))


def get_book_statuses():
    return fetch_all("SELECT id, title, status, read_year FROM books ORDER BY title")


def get_book_title(book_id):
    rows = fetch_all("SELECT title FROM books WHERE id = ?", (book_id,))
    return rows[0] if rows else None


def update_book_status(book_id, status, read_year=None):
    status = normalize_status(status, allow_empty=False)
    read_year = parse_year(read_year) if status == READ else None
    with connection() as conn:
        conn.execute("UPDATE books SET status = ?, read_year = ? WHERE id = ?",
                     (status, read_year, book_id))


def get_books_missing_read_year():
    return fetch_all("""
        SELECT id, title, status, read_year FROM books
        WHERE read_year IS NULL AND status = ? ORDER BY title
    """, (READ,))


def update_read_year(book_id, read_year):
    read_year = parse_year(read_year)
    with connection() as conn:
        conn.execute("UPDATE books SET read_year = ? WHERE id = ? AND status = ?",
                     (read_year, book_id, READ))
