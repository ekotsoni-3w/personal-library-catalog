"""Έλεγχοι με ξεχωριστή προσωρινή SQLite βάση ανά test."""

import contextlib
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from constants import READ, UNREAD

import api
import book_actions
import database
import reports
import main
import update_read_year
from init_db import init_db
from validation import parse_year, validate_isbn


class BooksTests(unittest.TestCase):
    def setUp(self):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        temp_dir = stack.enter_context(tempfile.TemporaryDirectory())
        self.db = Path(temp_dir) / 'books.db'
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(patch.object(database, 'DB_NAME', self.db))
        init_db(self.db)

    def rows(self, sql):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def test_manual_entry(self):
        with patch('builtins.input', side_effect=['Τίτλος', 'Συγγραφέας', 'Είδος', '2020', 'Διαβασμένο', 'Σημείωση', '2025']):
            book_actions.manual_entry('9780306406157')
        self.assertEqual(self.rows('SELECT title, year, status, notes, read_year FROM books'),
                         [('Τίτλος', 2020, READ, 'Σημείωση', 2025)])

    def test_isbn_menu_success(self):
        info = dict(title='Title', authors='Author', genres='Genre', year=2020, isbn='9780306406157')
        with patch.object(api, 'get_book_info_by_isbn', return_value=info), patch('builtins.input', side_effect=['1', '9780306406157', UNREAD, '', '9']):
            main.main()
        self.assertEqual(self.rows('SELECT title FROM books'), [('Title',)])

    def test_api_empty_and_failure(self):
        for data in ({}, {'items': []}, {'items': [{}]}, None):
            with self.subTest(data=data), patch.object(api.requests, 'get', return_value=Mock(json=Mock(return_value=data))):
                self.assertIsNone(api.get_book_info_by_isbn('9780306406157'))
        with patch.object(api.requests, 'get', side_effect=api.requests.Timeout):
            self.assertIsNone(api.get_book_info_by_isbn('9780306406157'))

    def test_api_success(self):
        response = Mock()
        response.json.return_value = {'items': [{'volumeInfo': {'title': 'Book', 'publishedDate': '2020-01'}}]}
        with patch.object(api.requests, 'get', return_value=response) as get:
            self.assertEqual(api.get_book_info_by_isbn('978-0-306-40615-7')['year'], 2020)
            self.assertEqual(get.call_args.kwargs, {'params': {'q': 'isbn:9780306406157'}, 'timeout': 10})

    def test_validation_before_write(self):
        for title, status, year in [('', UNREAD, 2020), ('Book', 'typo', 2020), ('Book', UNREAD, 'wrong')]:
            with self.assertRaises(ValueError):
                book_actions.add_book(title, 'Author', 'Genre', year, None, status, '')
        self.assertEqual(self.rows('SELECT * FROM authors'), [])

    def test_unread_clears_year(self):
        book_actions.add_book('Book', 'Author', 'Genre', 2020, None, READ, '', 2025)
        with patch('builtins.input', side_effect=['1', 'Αδιάβαστο']):
            book_actions.update_book_status()
        self.assertEqual(self.rows('SELECT status, read_year FROM books'), [(UNREAD, None)])

    def test_batch_only_read_books(self):
        book_actions.add_book('Unread', 'Author', 'Genre', None, None, 'Μη διαβασμένο', '')
        with patch('builtins.input', return_value=''):
            book_actions.add_book('Read', 'Author', 'Genre', None, None, READ, '')
        with patch('builtins.input', side_effect=['bad', '2024']) as inp:
            update_read_year.batch_update_read_year()
        self.assertEqual(inp.call_count, 2)
        self.assertEqual(self.rows('SELECT title, read_year FROM books ORDER BY title'), [('Read', 2024), ('Unread', None)])

    def test_migration_is_repeatable(self):
        book_actions.add_book('Book', 'Author', 'Genre', None, None, UNREAD, '')
        init_db(self.db)
        init_db(self.db)
        self.assertEqual(self.rows('SELECT title FROM books'), [('Book',)])

    def test_report_queries(self):
        database.add_book('Read', 'Author A', 'Genre', 2020, '9780306406157', READ, '', 2025)
        database.add_book('Unread', 'Author B', 'Genre', 2021, None)
        self.assertEqual(len(database.get_books()), 2)
        self.assertEqual([r[0] for r in database.get_books_by_status(UNREAD)], ['Unread'])
        self.assertEqual([r[0] for r in database.find_books_by_title('Unread')], ['Unread'])
        self.assertEqual([r[0] for r in database.find_books_by_author('Author A')], ['Read'])
        self.assertEqual([r[0] for r in database.get_books_by_author('Author B')], ['Unread'])
        self.assertEqual(database.get_year_counts(), [(2025, 1)])
        self.assertEqual(database.get_author_counts(), [('Author A', 1)])

    def test_reports_menu(self):
        database.add_book('Read', 'Author', 'Genre', 2020, '9780306406157', READ, '', 2025)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('builtins.input', side_effect=[
            '2', '4', '1', '5', '1', 'Read', '5', '2', 'Author', '6', 'Author', '9'
        ]):
            main.main()
        self.assertIn('Αποτελέσματα αναζήτησης', output.getvalue())
        self.assertGreaterEqual(output.getvalue().count('- Read (2020)'), 5)

    def test_database_transaction_rollback(self):
        with self.assertRaises(RuntimeError):
            with database.connection() as conn:
                conn.execute("INSERT INTO authors (name) VALUES ('Rollback')")
                raise RuntimeError('abort')
        self.assertEqual(self.rows('SELECT * FROM authors'), [])

    def test_valid_isbn(self):
        for value, expected in [
            ('978-0-306-40615-7', '9780306406157'),
            ('9791090636071', '9791090636071'),
            ('0-306-40615-2', '0306406152'),
            (' 0 8044 2957 x ', '080442957X'),
            ('978\t0306406157', '9780306406157'),
        ]:
            with self.subTest(value=value):
                self.assertEqual(validate_isbn(value), expected)

    def test_invalid_isbn(self):
        for value in ('', None, '---', '123', '9780306406158', '0306406153',
                      '978030640615X', 'X804429570', '９７８０３０６４０６１５７',
                      '4006381333931', '9780306406157!', 9780306406157):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_isbn(value)
        self.assertIsNone(validate_isbn(None, allow_empty=True))
        self.assertIsNone(validate_isbn('  ', allow_empty=True))

    def test_invalid_isbn_never_calls_api(self):
        with patch.object(api.requests, 'get') as get:
            with self.assertRaises(ValueError):
                api.get_book_info_by_isbn('9780306406158')
            get.assert_not_called()

    def test_invalid_isbn_menu(self):
        with patch.object(api, 'get_book_info_by_isbn') as lookup, patch(
            'builtins.input', side_effect=['1', '123', '9']
        ):
            main.main()
        lookup.assert_not_called()
        self.assertEqual(self.rows('SELECT * FROM books'), [])

    def test_isbn_storage(self):
        database.add_book('Book', 'Author', 'Genre', None, '0-306-40615-2')
        self.assertEqual(self.rows('SELECT isbn FROM books'), [('0306406152',)])
        with self.assertRaises(ValueError):
            database.add_book('Bad', 'New Author', 'New Genre', None, '123')
        self.assertEqual(self.rows('SELECT name FROM authors'), [('Author',)])
        with patch('builtins.input') as inp:
            with self.assertRaises(ValueError):
                book_actions.add_book('Bad', 'Author', 'Genre', None, '123')
            inp.assert_not_called()

    def test_duplicate_isbn_equivalence(self):
        book_id = database.add_book('Original', 'Author', 'Genre', None, '0306406152')
        for isbn in ('0306406152', '978-0-306-40615-7'):
            with self.subTest(isbn=isbn), self.assertRaises(database.DuplicateBookError) as error:
                database.add_book('Other title', 'Other author', 'Other genre', None, isbn)
            self.assertEqual(error.exception.book_id, book_id)
        self.assertEqual(self.rows('SELECT title FROM books'), [('Original',)])
        self.assertEqual(self.rows('SELECT name FROM authors'), [('Author',)])
        self.assertEqual(self.rows('SELECT name FROM genres'), [('Genre',)])

    def test_duplicate_without_isbn(self):
        database.add_book('Το Βιβλίο', 'Ο Συγγραφέας', 'Genre', None, None)
        for isbn in (None, '9780306406157'):
            with self.subTest(isbn=isbn), self.assertRaises(database.DuplicateBookError):
                database.add_book('  το   βιβλίο ', 'ο συγγραφέας', 'Genre', 2025, isbn)
        database.add_book('Το Βιβλίο', 'Άλλος συγγραφέας', 'Genre', None, None)
        self.assertEqual(len(database.get_books()), 2)

    def test_distinct_editions_and_missing_isbn(self):
        database.add_book('Book', 'Author', 'Genre', None, '9780306406157')
        database.add_book('Book', 'Author', 'Genre', None, '9791090636071')
        with self.assertRaises(database.DuplicateBookError):
            database.add_book('Book', 'Author', 'Genre', None, None)
        self.assertEqual(len(database.get_books()), 2)

    def test_duplicate_menu_skips_api(self):
        database.add_book('Book', 'Author', 'Genre', None, '0306406152')
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(api, 'get_book_info_by_isbn') as lookup, patch(
            'builtins.input', side_effect=['1', '9780306406157', '9']
        ):
            main.main()
        lookup.assert_not_called()
        self.assertIn('υπάρχει ήδη', output.getvalue())

    def test_duplicate_action_skips_prompts(self):
        database.add_book('Book', 'Author', 'Genre', None, None)
        with patch('builtins.input') as inp, self.assertRaises(database.DuplicateBookError):
            book_actions.add_book('Book', 'Author', 'Genre', None, None)
        inp.assert_not_called()

    def test_legacy_formatted_isbn(self):
        database.add_book('Book', 'Author', 'Genre', None, None)
        with database.connection() as conn:
            conn.execute("UPDATE books SET isbn = '0-306-40615-2'")
        with self.assertRaises(database.DuplicateBookError):
            database.add_book('Other', 'Other', 'Genre', None, '9780306406157')
        self.assertEqual(self.rows('SELECT isbn FROM books'), [('0-306-40615-2',)])

    def test_books_reuse_author_and_genre(self):
        first = database.add_book('First', 'Author', 'Genre', 2020, None)
        second = database.add_book('Second', 'Author', 'Genre', 2021, None)
        self.assertNotEqual(first, second)
        self.assertEqual(self.rows('SELECT COUNT(*) FROM authors'), [(1,)])
        self.assertEqual(self.rows('SELECT COUNT(*) FROM genres'), [(1,)])
        self.assertEqual(self.rows(
            'SELECT COUNT(DISTINCT author_id), COUNT(DISTINCT genre_id) FROM books'
        ), [(1, 1)])

    def test_failed_book_insert_rolls_back_related_records(self):
        # Προσομοιώνει σφάλμα SQLite αφού δημιουργηθούν συγγραφέας και είδος.
        with database.connection() as conn:
            conn.execute("""
                CREATE TRIGGER reject_book BEFORE INSERT ON books
                BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END
            """)
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'simulated write failure'):
            database.add_book('Book', 'New author', 'New genre', None, None)
        for table in ('books', 'authors', 'genres'):
            with self.subTest(table=table):
                self.assertEqual(self.rows(f'SELECT COUNT(*) FROM {table}'), [(0,)])

    def test_invalid_status_update_preserves_existing_data(self):
        book_id = database.add_book('Book', 'Author', 'Genre', None, None, READ, 'Notes', 2024)
        for status, year in [('invalid', 2025), (READ, 'bad year')]:
            with self.subTest(status=status, year=year), self.assertRaises(ValueError):
                database.update_book_status(book_id, status, year)
            self.assertEqual(self.rows('SELECT status, read_year, notes FROM books'),
                             [(READ, 2024, 'Notes')])

    def test_statistics_count_only_eligible_books(self):
        database.add_book('One', 'Author A', 'Genre', None, None, READ, '', 2024)
        database.add_book('Two', 'Author A', 'Genre', None, None, READ, '', 2024)
        database.add_book('Three', 'Author B', 'Genre', None, None, READ, '', 2025)
        database.add_book('No year', 'Author A', 'Genre', None, None, READ)
        database.add_book('Unread', 'Author B', 'Genre', None, None, UNREAD)
        self.assertEqual(database.get_year_counts(), [(2024, 2), (2025, 1)])
        self.assertEqual(database.get_author_counts(), [('Author A', 3), ('Author B', 1)])
        self.assertEqual([r[1] for r in database.get_books_missing_read_year()], ['No year'])

    def test_migration_from_old_schema_preserves_book(self):
        legacy_db = self.db.parent / 'legacy.db'
        with contextlib.closing(sqlite3.connect(legacy_db)) as conn:
            conn.executescript("""
                CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE genres (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE books (
                    id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                    author_id INTEGER, genre_id INTEGER, year INTEGER
                );
                INSERT INTO authors VALUES (1, 'Author');
                INSERT INTO genres VALUES (1, 'Genre');
                INSERT INTO books VALUES (1, 'Legacy book', 1, 1, 1999);
            """)
        with patch.object(database, 'DB_NAME', legacy_db):
            init_db()
            init_db()
            self.assertEqual(database.get_books(),
                             [('Legacy book', 'Author', 'Genre', 1999, None, None, None)])
            database.update_book_status(1, READ, 2024)
            self.assertEqual(database.get_year_counts(), [(2024, 1)])
        self.assertEqual(self.rows('SELECT * FROM books'), [])

    def test_year_validation(self):
        for value in ('²', '0', '-1', '10000', '2020.5'):
            with self.assertRaises(ValueError):
                parse_year(value)
        self.assertEqual(parse_year(' 2020 '), 2020)
        self.assertIsNone(parse_year(''))


if __name__ == '__main__':
    unittest.main()
