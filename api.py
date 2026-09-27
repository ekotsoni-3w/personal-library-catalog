"""Αναζήτηση στοιχείων βιβλίου στο Google Books."""

import requests

from validation import validate_isbn


def get_book_info_by_isbn(isbn):
    isbn = validate_isbn(isbn)
    try:
        response = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": f"isbn:{isbn}"}, timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        print("Δεν ήταν δυνατή η αναζήτηση στο Google Books.")
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("items")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        return None
    info = items[0].get("volumeInfo")
    if not isinstance(info, dict):
        return None

    title = info.get("title", "Άγνωστος τίτλος")
    authors = ", ".join((info.get("authors") or ["Άγνωστος"]))
    categories = ", ".join((info.get("categories") or ["Άγνωστο είδος"]))
    published_date = info.get("publishedDate", "")
    year = None
    if isinstance(published_date, str) and published_date[:4].isascii() and published_date[:4].isdigit():
        year = int(published_date[:4])

    return {
        "title": title,
        "authors": authors,
        "genres": categories,
        "year": year,
        "isbn": isbn
    }
