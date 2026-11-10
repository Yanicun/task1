import unittest
from unittest.mock import patch

from project import app, db
from project.books.models import Book
from project.customers.models import Customer
from project.validation import validate_text


PAYLOADS = [
    '<script>alert("XSS")</script>',
    '<img src=x onerror="document.body.prepend(\'XSS\')">',
    '<svg onload=alert(1)>',
    '&lt;script&gt;alert(1)&lt;/script&gt;',
]


class ValidationTests(unittest.TestCase):
    def test_valid_text(self):
        for value in ['Żółć', "O'Connor", 'Harry Potter 2: Powrót!', 'Łódź', 'A' * 64]:
            with self.subTest(value=value):
                self.assertEqual(validate_text('name', value), value)
        self.assertEqual(validate_text('name', '  Solaris  '), 'Solaris')

    def test_invalid_text(self):
        for value in PAYLOADS + ['', '   ', 'A' * 65, None, 123, [], {}, 'a\nb', 'a\x00b']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_text('name', value)

    def test_models_validate_creation(self):
        for payload in PAYLOADS:
            for field in ['name', 'author']:
                data = dict(name='Solaris', author='Stanisław Lem', year_published=1961, book_type='2days')
                data[field] = payload
                with self.subTest(model='Book', field=field, payload=payload):
                    with self.assertRaises(ValueError):
                        Book(**data)
            for field in ['name', 'city']:
                data = dict(name='Jan Kowalski', city='Łódź', age=25)
                data[field] = payload
                with self.subTest(model='Customer', field=field, payload=payload):
                    with self.assertRaises(ValueError):
                        Customer(**data)

    def test_models_validate_assignment(self):
        objects = [(Book('Solaris', 'Stanisław Lem', 1961, '2days'), ['name', 'author']),
                   (Customer('Jan Kowalski', 'Łódź', 25), ['name', 'city'])]
        for obj, fields in objects:
            for field in fields:
                original = getattr(obj, field)
                with self.subTest(field=field, model=type(obj).__name__):
                    with self.assertRaises(ValueError):
                        setattr(obj, field, PAYLOADS[0])
                    self.assertEqual(getattr(obj, field), original)


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.context = app.app_context()
        self.context.push()
        self.client = app.test_client()
        # Zamiast commit używam flush, żeby po teście cofnąć dane.
        self.commit = patch.object(db.session, 'commit', side_effect=db.session.flush)
        self.commit.start()

    def tearDown(self):
        db.session.rollback()
        self.commit.stop()
        db.session.remove()
        self.context.pop()

    def test_book_create_and_edit(self):
        data = dict(name='Test książki', author='Stanisław Lem', year_published='1961', book_type='2days')
        self.assertEqual(self.client.post('/books/create', json=data).status_code, 302)
        book = Book.query.filter_by(name=data['name']).one()
        book_id = book.id
        url = f'/books/{book_id}/edit'
        self.assertEqual(self.client.post(url, json={'author': "O'Connor"}).status_code, 200)
        self.assertIn('Test książki', self.client.get('/books/').get_data(as_text=True))

    def test_book_rejects_invalid_edit(self):
        for field in ['name', 'author']:
            book = Book('Test edycji', 'Stanisław Lem', 1961, '2days')
            db.session.add(book)
            db.session.flush()
            response = self.client.post(f'/books/{book.id}/edit', json={field: PAYLOADS[0]})
            self.assertEqual(response.status_code, 400)
            self.assertIn('unsupported', response.get_json()['error'])

    def test_book_rejects_invalid_creation(self):
        count = Book.query.count()
        for field in ['name', 'author']:
            data = dict(name='Test XSS', author='Jan', year_published='2024', book_type='2days')
            data[field] = PAYLOADS[1]
            self.assertEqual(self.client.post('/books/create', json=data).status_code, 400)
        self.assertEqual(Book.query.count(), count)
        for data in [{}, [], None]:
            self.assertEqual(self.client.post('/books/create', json=data, content_type='application/json').status_code, 400)

    def test_customer_create_and_edit(self):
        data = dict(name='Test czytelnika', city='Łódź', age='25')
        self.assertEqual(self.client.post('/customers/create', data=data).status_code, 302)
        customer = Customer.query.filter_by(name=data['name']).one()
        url = f'/customers/{customer.id}/edit'
        data['city'] = 'Warszawa'
        self.assertEqual(self.client.post(url, data=data).status_code, 302)
        self.assertEqual(Customer.query.filter_by(name=data['name']).one().city, 'Warszawa')

    def test_customer_rejects_invalid_edit(self):
        for field in ['name', 'city']:
            customer = Customer('Test edycji', 'Łódź', 25)
            db.session.add(customer)
            db.session.flush()
            url = f'/customers/{customer.id}/edit'
            invalid = dict(name='Test edycji', city='Łódź', age='25')
            invalid[field] = PAYLOADS[0]
            self.assertEqual(self.client.post(url, data=invalid).status_code, 400)

    def test_customer_rejects_invalid_creation(self):
        count = Customer.query.count()
        for field in ['name', 'city']:
            data = dict(name='Test XSS', city='Łódź', age='25')
            data[field] = PAYLOADS[1]
            self.assertEqual(self.client.post('/customers/create', data=data).status_code, 400)
        self.assertEqual(Customer.query.count(), count)
        self.assertEqual(self.client.post('/customers/create', data={}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
