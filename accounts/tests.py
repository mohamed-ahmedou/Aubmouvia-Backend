from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='amina', password='Ledger-2026')

    def test_login_and_me(self):
        closed = self.client.post(
            '/api/auth/register/',
            {'username': 'autre', 'password': 'Ledger-2026'},
            format='json',
        )
        self.assertEqual(closed.status_code, 404)
        self.assertFalse(User.objects.filter(username='autre').exists())

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'amina', 'password': 'Ledger-2026'},
            format='json',
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data['user']['username'], 'amina')
        self.assertFalse(login.data['user']['superuser'])

        me = self.client.get(
            '/api/auth/me/',
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['username'], 'amina')
        self.assertFalse(me.data['superuser'])

        anonymous = self.client.get('/api/auth/me/')
        self.assertEqual(anonymous.status_code, 401)

        rejected = self.client.post(
            '/api/auth/login/',
            {'username': 'amina', 'password': 'mauvais-mot'},
            format='json',
        )
        self.assertEqual(rejected.status_code, 401)


class AccountRoleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='med', password='Ledger-2026')
        self.member = User.objects.create_user(username='amina', password='Ledger-2026')

    def token(self, username):
        login = self.client.post(
            '/api/auth/login/',
            {'username': username, 'password': 'Ledger-2026'},
            format='json',
        )
        return login.data['access']

    def test_only_superuser_manages_accounts(self):
        denied = self.client.get(
            '/api/auth/accounts/',
            HTTP_AUTHORIZATION=f'Bearer {self.token("amina")}',
        )
        self.assertEqual(denied.status_code, 403)

        listed = self.client.get(
            '/api/auth/accounts/',
            HTTP_AUTHORIZATION=f'Bearer {self.token("med")}',
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            {item['username']: item['superuser'] for item in listed.data},
            {'amina': False, 'med': True},
        )

        created = self.client.post(
            '/api/auth/accounts/',
            {
                'username': 'sara',
                'name': 'Sara Benali',
                'email': 'sara@example.com',
                'password': 'Ledger-2026',
                'superuser': True,
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token("med")}',
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data['superuser'])
        self.assertEqual(created.data['name'], 'Sara Benali')
        self.assertEqual(created.data['email'], 'sara@example.com')
        sara = User.objects.get(username='sara')
        self.assertTrue(sara.is_staff)

        demoted = self.client.patch(
            f'/api/auth/accounts/{sara.pk}/',
            {
                'username': 'sara.b',
                'name': 'Sara B.',
                'email': 'sara.b@example.com',
                'password': 'Ledger-2027',
                'superuser': False,
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token("med")}',
        )
        self.assertEqual(demoted.status_code, 200)
        self.assertFalse(demoted.data['superuser'])
        self.assertEqual(demoted.data['username'], 'sara.b')
        self.assertEqual(demoted.data['name'], 'Sara B.')
        self.assertEqual(demoted.data['email'], 'sara.b@example.com')
        sara.refresh_from_db()
        self.assertTrue(sara.check_password('Ledger-2027'))

        own_role = self.client.patch(
            f'/api/auth/accounts/{self.admin.pk}/',
            {'superuser': False},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {self.token("med")}',
        )
        self.assertEqual(own_role.status_code, 400)

        removed = self.client.delete(
            f'/api/auth/accounts/{sara.pk}/',
            HTTP_AUTHORIZATION=f'Bearer {self.token("med")}',
        )
        self.assertEqual(removed.status_code, 204)
        self.assertFalse(User.objects.filter(username='sara').exists())


class HistoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='amina', password='Ledger-2026')

    def test_records_import_and_lists_it(self):
        login = self.client.post(
            '/api/auth/login/',
            {'username': 'amina', 'password': 'Ledger-2026'},
            format='json',
        )
        token = login.data['access']
        created = self.client.post(
            '/api/auth/history/',
            {'kind': 'import', 'fileName': 'salaires.xlsx', 'detail': 'Septembre', 'lines': 12},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['username'], 'amina')

        listed = self.client.get('/api/auth/history/', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]['fileName'], 'salaires.xlsx')
        self.assertEqual(listed.data[0]['kind'], 'import')
        self.assertEqual(listed.data[0]['lines'], 12)

        rejected = self.client.post(
            '/api/auth/history/',
            {'kind': 'autre', 'fileName': 'salaires.xlsx', 'lines': 1},
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(rejected.status_code, 400)
