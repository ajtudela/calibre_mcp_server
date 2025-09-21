
import os
import sqlite3
from typing import List, Tuple, Generator
from contextlib import contextmanager


@contextmanager
def database_connection(
    db_path: str
) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for SQLite database connections.

    Args:
        db_path (str): Path to the SQLite database file.

    Yields:
        sqlite3.Connection: Database connection object.

    Raises:
        sqlite3.Error: If there is a database connection error.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


class Book:
    """
    Represents a book with its metadata from the Calibre database.
    """

    def __init__(
        self,
        id: int,
        library_path: str,
        db_filename: str = 'metadata.db'
    ):
        """
        Initialize a Book instance with the path to the Calibre library and
        database filename.

        Args:
            id (int): Book ID.
            library_path (str): Path to the Calibre library folder.
            db_filename (str): Name of the SQLite database file
                (default: 'metadata.db').

        Raises:
            ValueError: If the book ID is not found in the database.
            sqlite3.Error: If there is a database error.
        """
        if not isinstance(id, int) or id <= 0:
            raise ValueError("Book ID must be a positive integer")

        self.id = id
        self.title = ''
        self.title_sort = ''
        self.date = ''
        self.author = ''
        self.author_sort = ''
        self.series = ''
        self.series_sort = ''
        self.series_idx = 0.0
        self.publisher = ''
        self.identifiers = ''
        self.language = ''
        self.synopsis = ''
        self.tags = ''

        if not library_path or not isinstance(library_path, str):
            raise ValueError("Library path must be a non-empty string")

        self.db_path = os.path.join(library_path, db_filename)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        self._load_book_data(self.db_path)

    def _load_book_data(self, db_path: str) -> None:
        """
        Load all book data from the database in a single optimized query.

        Args:
            db_path (str): Path to the SQLite database file.

        Raises:
            ValueError: If the book ID is not found.
            sqlite3.Error: If there is a database error.
        """
        try:
            with database_connection(db_path) as conn:
                cursor = conn.cursor()

                # Single comprehensive query to get all book data at once
                cursor.execute("""
                    SELECT
                        b.title,
                        b.sort,
                        b.pubdate,
                        b.series_index,
                        GROUP_CONCAT(DISTINCT a.name ORDER BY a.name)
                        as authors,
                        GROUP_CONCAT(DISTINCT a.sort ORDER BY a.sort)
                        as author_sorts,
                        s.name as series_name,
                        s.sort as series_sort,
                        GROUP_CONCAT(DISTINCT p.name ORDER BY p.name)
                        as publishers,
                        GROUP_CONCAT(DISTINCT i.type || ':' || i.val
                                     ORDER BY i.type) as identifiers,
                        l.lang_code as language,
                        c.text as synopsis,
                        GROUP_CONCAT(DISTINCT t.name ORDER BY t.name) as tags
                    FROM books b
                    LEFT JOIN books_authors_link bal ON b.id = bal.book
                    LEFT JOIN authors a ON bal.author = a.id
                    LEFT JOIN books_series_link bsl ON b.id = bsl.series
                    LEFT JOIN series s ON bsl.series = s.id
                    LEFT JOIN books_publishers_link bpl ON b.id = bpl.book
                    LEFT JOIN publishers p ON bpl.publisher = p.id
                    LEFT JOIN identifiers i ON b.id = i.book
                    LEFT JOIN books_languages_link bll ON b.id = bll.book
                    LEFT JOIN languages l ON bll.lang_code = l.id
                    LEFT JOIN comments c ON b.id = c.book
                    LEFT JOIN books_tags_link btl ON b.id = btl.book
                    LEFT JOIN tags t ON btl.tag = t.id
                    WHERE b.id = ?
                    GROUP BY b.id, b.title, b.sort, b.pubdate, b.series_index,
                             s.name, s.sort, l.lang_code, c.text
                """, (self.id,))

                result = cursor.fetchone()
                if not result:
                    raise ValueError(f"Book with ID {self.id} not found")

                # Assign all values from the single query
                self.title = result[0] or ''
                self.title_sort = result[1] or ''
                self.date = result[2] or ''
                self.series_idx = result[3] or 0.0
                self.author = result[4] or ''
                self.author_sort = result[5] or ''
                self.series = result[6] or ''
                self.series_sort = result[7] or ''
                self.publisher = result[8] or ''
                self.identifiers = result[9] or ''
                self.language = result[10] or ''
                self.synopsis = result[11] or ''
                self.tags = result[12] or ''

                # Clean up concatenated strings
                if self.author:
                    self.author = self.author.replace(',', ' & ')
                if self.author_sort:
                    self.author_sort = self.author_sort.replace(',', ' & ')
                if self.publisher:
                    self.publisher = self.publisher.replace(',', ' & ')
                if self.identifiers:
                    self.identifiers = self.identifiers.replace(',', ', ')
                if self.tags:
                    self.tags = self.tags.replace(',', ', ')

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error while loading book {self.id}: {e}"
            )

    def to_json(self) -> dict:
        """
        Return the book as a JSON-compatible dictionary.

        Returns:
            dict: Dictionary containing all book metadata.
        """
        return {
            "id": self.id,
            "title": self.title,
            "title_sort": self.title_sort,
            "date": self.date,
            "author": self.author,
            "author_sort": self.author_sort,
            "series": self.series,
            "series_sort": self.series_sort,
            "series_idx": self.series_idx,
            "publisher": self.publisher,
            "identifiers": self.identifiers,
            "language": self.language,
            "tags": self.tags,
            "synopsis": self.synopsis
        }

    def __str__(self) -> str:
        """
        Return a string representation of the book.

        Returns:
            str: Human-readable string representation.
        """
        return (f"Book(id={self.id}, title='{self.title}', "
                f"author='{self.author}')")

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            str: Detailed string representation.
        """
        return (f"Book(id={self.id}, title='{self.title}', "
                f"author='{self.author}', series='{self.series}')")


class CalibreDB:
    """
    Class to manage SQLite operations for Calibre database.
    """

    def __init__(self, library_path: str, db_filename: str = 'metadata.db'):
        """
        Initialize CalibreDB with the path to the Calibre library and
        database filename.

        Args:
            library_path (str): Path to the Calibre library folder.
            db_filename (str): Name of the SQLite database file
                (default: 'metadata.db').

        Raises:
            ValueError: If library_path is empty or invalid.
            FileNotFoundError: If the database file doesn't exist.
        """
        if not library_path or not isinstance(library_path, str):
            raise ValueError("Library path must be a non-empty string")

        self.db_path = os.path.join(library_path, db_filename)
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

    def search_books_by_title(
        self, title_pattern: str
    ) -> List[Tuple[int, str]]:
        """
        Search for books by title matching a pattern.

        Args:
            title_pattern (str): Pattern to search for in titles
                (supports % wildcards).

        Returns:
            List[Tuple[int, str]]: List of (book_id, title) tuples.

        Raises:
            ValueError: If pattern is empty.
            sqlite3.Error: If there is a database error.
        """
        if not title_pattern or not isinstance(title_pattern, str):
            raise ValueError("Title pattern must be a non-empty string")

        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, title FROM books WHERE title LIKE ? '
                    'ORDER BY title',
                    (title_pattern,)
                )
                return cursor.fetchall()

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error searching books by title pattern "
                f"'{title_pattern}': {e}"
            )

    def search_authors_by_name(
        self, name_pattern: str
    ) -> List[Tuple[int, str]]:
        """
        Search for authors by name matching a pattern.

        Args:
            name_pattern (str): Pattern to search for in names
                (supports % wildcards).

        Returns:
            List[Tuple[int, str]]: List of (author_id, name) tuples.

        Raises:
            ValueError: If pattern is empty.
            sqlite3.Error: If there is a database error.
        """
        if not name_pattern or not isinstance(name_pattern, str):
            raise ValueError("Name pattern must be a non-empty string")

        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, name FROM authors WHERE name LIKE ? '
                    'ORDER BY name',
                    (name_pattern,)
                )
                return cursor.fetchall()

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error searching authors by name pattern "
                f"'{name_pattern}': {e}"
            )

    def search_books_by_tag(
        self, tag_pattern: str
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about all books with tags matching a pattern.

        Args:
            tag_pattern (str): Pattern to search for in tag names
                (supports % wildcards).

        Returns:
            List[Tuple[int, str, str, str]]: List of (book_id, title,
                author_name, publication_date) tuples, ordered by title.

        Raises:
            ValueError: If pattern is empty or no books found.
            sqlite3.Error: If there is a database error.
        """
        if not tag_pattern or not isinstance(tag_pattern, str):
            raise ValueError("Tag pattern must be a non-empty string")

        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT b.id, b.title,
                           COALESCE(GROUP_CONCAT(a.name, ' & '), '')
                           as authors,
                           b.pubdate
                    FROM books b
                    JOIN books_tags_link btl ON b.id = btl.book
                    JOIN tags t ON btl.tag = t.id
                    LEFT JOIN books_authors_link bal ON b.id = bal.book
                    LEFT JOIN authors a ON bal.author = a.id
                    WHERE t.name LIKE ?
                    GROUP BY b.id, b.title, b.pubdate
                    ORDER BY b.title
                """, (tag_pattern,))

                results = cursor.fetchall()
                if not results:
                    raise ValueError(
                        f"No books found with tag pattern '{tag_pattern}'"
                    )

                return results

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error getting books with tag pattern "
                f"'{tag_pattern}': {e}"
            )

    def get_books_by_author(
        self, author_name: str
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about all books by a specific author.

        Args:
            author_name (str): Name of the author.

        Returns:
            List[Tuple[int, str, str, str]]: List of (book_id, title,
                publication_date, series_info) tuples, ordered by
                publication date.

        Raises:
            ValueError: If author name is empty or author not found.
            sqlite3.Error: If there is a database error.
        """
        if not author_name or not isinstance(author_name, str):
            raise ValueError("Author name must be a non-empty string")

        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT b.id, b.title, b.pubdate,
                           CASE
                               WHEN s.name IS NOT NULL
                               THEN s.name || ' #' ||
                                    CAST(b.series_index AS TEXT)
                               ELSE ''
                           END as series_info
                    FROM books b
                    JOIN books_authors_link bal ON b.id = bal.book
                    JOIN authors a ON bal.author = a.id
                    LEFT JOIN books_series_link bsl ON b.id = bsl.book
                    LEFT JOIN series s ON bsl.series = s.id
                    WHERE a.name = ?
                    ORDER BY b.pubdate DESC, b.title
                """, (author_name,))

                results = cursor.fetchall()
                if not results:
                    raise ValueError(
                        f"No books found for author '{author_name}'"
                    )

                return results

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error getting books for author '{author_name}': {e}"
            )

    def get_books_by_author_id(
        self, author_id: int
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about all books by a specific author ID.

        Args:
            author_id (int): ID of the author.

        Returns:
            List[Tuple[int, str, str, str]]: List of (book_id, title,
                publication_date, series_info) tuples, ordered by
                publication date.

        Raises:
            ValueError: If author_id is not a positive integer or no
                books found.
            sqlite3.Error: If there is a database error.
        """
        if not isinstance(author_id, int) or author_id <= 0:
            raise ValueError("Author ID must be a positive integer")

        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT b.id, b.title, b.pubdate,
                           CASE
                               WHEN s.name IS NOT NULL
                               THEN s.name || ' #' ||
                                    CAST(b.series_index AS TEXT)
                               ELSE ''
                           END as series_info
                    FROM books b
                    JOIN books_authors_link bal ON b.id = bal.book
                    LEFT JOIN books_series_link bsl ON b.id = bsl.book
                    LEFT JOIN series s ON bsl.series = s.id
                    WHERE bal.author = ?
                    ORDER BY b.pubdate DESC, b.title
                """, (author_id,))

                results = cursor.fetchall()
                if not results:
                    raise ValueError(
                        f"No books found for author ID {author_id}"
                    )

                return results

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error getting books for author ID {author_id}: {e}"
            )

    def get_books_by_series(
        self, series_name: str
    ) -> List[Tuple[int, str, float]]:
        """
        Get all books in a specific series.

        Args:
            series_name (str): Name of the series.

        Returns:
            List[Tuple[int, str, float]]: List of (book_id, title,
                series_index) tuples, ordered by series index.

        Raises:
            ValueError: If series name is empty or series not found.
            sqlite3.Error: If there is a database error.
        """
        if not series_name or not isinstance(series_name, str):
            raise ValueError("Series name must be a non-empty string")

        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.id, b.title, b.series_index
                    FROM books b
                    JOIN books_series_link bsl ON b.id = bsl.book
                    JOIN series s ON bsl.series = s.id
                    WHERE s.name = ?
                    ORDER BY b.series_index
                """, (series_name,))

                results = cursor.fetchall()
                if not results:
                    raise ValueError(
                        f"No books found for series '{series_name}'"
                    )

                return results

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error getting books for series "
                f"'{series_name}': {e}"
            )

    def get_books_by_tag(
        self, tag_name: str
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about all books with a specific tag.

        Args:
            tag_name (str): Name of the tag to search for.

        Returns:
            List[Tuple[int, str, str, str]]: List of (book_id, title,
                author_name, publication_date) tuples, ordered by title.

        Raises:
            ValueError: If tag name is empty or no books found with that tag.
            sqlite3.Error: If there is a database error.
        """
        if not tag_name or not isinstance(tag_name, str):
            raise ValueError("Tag name must be a non-empty string")

        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT b.id, b.title,
                           COALESCE(GROUP_CONCAT(a.name, ' & '), '')
                           as authors,
                           b.pubdate
                    FROM books b
                    JOIN books_tags_link btl ON b.id = btl.book
                    JOIN tags t ON btl.tag = t.id
                    LEFT JOIN books_authors_link bal ON b.id = bal.book
                    LEFT JOIN authors a ON bal.author = a.id
                    WHERE t.name = ?
                    GROUP BY b.id, b.title, b.pubdate
                    ORDER BY b.title
                """, (tag_name,))

                results = cursor.fetchall()
                if not results:
                    raise ValueError(f"No books found with tag '{tag_name}'")

                return results

        except sqlite3.Error as e:
            raise sqlite3.Error(
                f"Database error getting books with tag '{tag_name}': {e}"
            )

    def get_all_tags(self) -> List[Tuple[int, str]]:
        """
        Get all available tags in the database.

        Returns:
            List[Tuple[int, str]]: List of (tag_id, tag_name) tuples,
                ordered alphabetically by name.

        Raises:
            sqlite3.Error: If there is a database error.
        """
        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.id, t.name
                    FROM tags t
                    ORDER BY t.name
                """)
                return cursor.fetchall()

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Database error getting all tags: {e}")

    def get_book_count(self) -> int:
        """
        Get the total number of books in the database.

        Returns:
            int: Total number of books.

        Raises:
            sqlite3.Error: If there is a database error.
        """
        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM books')
                result = cursor.fetchone()
                return int(result[0])

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Database error counting books: {e}")

    def get_author_count(self) -> int:
        """
        Get the total number of authors in the database.

        Returns:
            int: Total number of authors.

        Raises:
            sqlite3.Error: If there is a database error.
        """
        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM authors')
                result = cursor.fetchone()
                return int(result[0])

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Database error counting authors: {e}")

    def get_database_info(self) -> dict:
        """
        Get comprehensive information about the database.

        Returns:
            dict: Dictionary containing database statistics.

        Raises:
            sqlite3.Error: If there is a database error.
        """
        try:
            info = {
                'db_path': self.db_path,
                'books_count': self.get_book_count(),
                'authors_count': self.get_author_count(),
            }

            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()

                # Get series count
                cursor.execute('SELECT COUNT(*) FROM series')
                info['series_count'] = cursor.fetchone()[0]

                # Get publishers count
                cursor.execute('SELECT COUNT(*) FROM publishers')
                info['publishers_count'] = cursor.fetchone()[0]

                # Get tags count
                cursor.execute('SELECT COUNT(*) FROM tags')
                info['tags_count'] = cursor.fetchone()[0]

                # Get languages count
                cursor.execute('SELECT COUNT(*) FROM languages')
                info['languages_count'] = cursor.fetchone()[0]

            return info

        except sqlite3.Error as e:
            raise sqlite3.Error(f"Database error getting database info: {e}")
