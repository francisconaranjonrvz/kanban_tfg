# Tests de la API de tableros, columnas, etiquetas y miembros.

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from boards.models import Board, BoardMembership, Column, Label

User = get_user_model()


class BoardsAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(username='alice', password='alicepass1')
        cls.bob = User.objects.create_user(username='bob', password='bobpass1234')

    def auth(self, user):
        resp = self.client.post(
            '/api/v1/auth/token/',
            {'username': user.username, 'password': 'alicepass1' if user.username == 'alice' else 'bobpass1234'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + resp.data['access'])

    # --- Tableros ---

    def test_create_and_list_board(self):
        self.auth(self.alice)
        r = self.client.post('/api/v1/boards/', {'name': 'TFG', 'description': 'x'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data['name'], 'TFG')

        r = self.client.get('/api/v1/boards/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data), 1)

    def test_isolation_between_users(self):
        b = Board.objects.create(owner=self.alice, name='Solo Alice')
        self.auth(self.bob)
        self.assertEqual(self.client.get('/api/v1/boards/').data, [])
        self.assertEqual(
            self.client.get(f'/api/v1/boards/{b.id}/').status_code, status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(f'/api/v1/boards/{b.id}/').status_code, status.HTTP_404_NOT_FOUND,
        )

    # --- Columnas + reordenar ---

    def test_columns_get_sequential_orders(self):
        self.auth(self.alice)
        b = Board.objects.create(owner=self.alice, name='B')
        for title in ('A', 'B', 'C'):
            self.client.post(f'/api/v1/boards/{b.id}/columns/', {'title': title}, format='json')
        cols = list(b.columns.order_by('order'))
        self.assertEqual([c.order for c in cols], [0, 1, 2])

    def test_column_move_reorders_and_avoids_unique_collision(self):
        self.auth(self.alice)
        b = Board.objects.create(owner=self.alice, name='B')
        c1 = Column.objects.create(board=b, title='A', order=0)
        c2 = Column.objects.create(board=b, title='B', order=1)
        c3 = Column.objects.create(board=b, title='C', order=2)
        r = self.client.post(f'/api/v1/boards/{b.id}/columns/{c3.id}/move/', {'order': 0}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        c1.refresh_from_db(); c2.refresh_from_db(); c3.refresh_from_db()
        self.assertEqual([c3.order, c1.order, c2.order], [0, 1, 2])

    # --- Tarjetas: crear + mover + permisos ---

    def test_card_move_reorders_within_and_across_columns(self):
        self.auth(self.alice)
        b = Board.objects.create(owner=self.alice, name='B')
        col1 = Column.objects.create(board=b, title='To Do', order=0)
        col2 = Column.objects.create(board=b, title='Done', order=1)
        c1 = self.client.post('/api/v1/tasks/', {'title': 'one', 'column': col1.id}, format='json').data
        c2 = self.client.post('/api/v1/tasks/', {'title': 'two', 'column': col1.id}, format='json').data
        r = self.client.post(f'/api/v1/tasks/{c2["id"]}/move/', {'column_id': col2.id, 'order': 0}, format='json')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        from tasks.models import Card
        c1_db = Card.objects.get(pk=c1['id'])
        c2_db = Card.objects.get(pk=c2['id'])
        self.assertEqual((c1_db.column_id, c1_db.order), (col1.id, 0))
        self.assertEqual((c2_db.column_id, c2_db.order), (col2.id, 0))

    def test_other_user_cannot_move_my_card(self):
        b = Board.objects.create(owner=self.alice, name='B')
        col = Column.objects.create(board=b, title='X', order=0)
        from tasks.models import Card
        card = Card.objects.create(column=col, title='secret', order=0)
        self.auth(self.bob)
        r = self.client.post(f'/api/v1/tasks/{card.id}/move/', {'column_id': col.id, 'order': 1}, format='json')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    # --- Miembros ---

    def test_owner_can_invite_and_remove_member(self):
        self.auth(self.alice)
        b = Board.objects.create(owner=self.alice, name='Shared')
        r = self.client.post(f'/api/v1/boards/{b.id}/members/', {'username': 'bob'}, format='json')
        self.assertIn(r.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertTrue(BoardMembership.objects.filter(board=b, user=self.bob).exists())

        self.auth(self.bob)
        self.assertEqual(self.client.get(f'/api/v1/boards/{b.id}/').status_code, status.HTTP_200_OK)

        r = self.client.post(f'/api/v1/boards/{b.id}/members/', {'username': 'alice'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

        self.auth(self.alice)
        r = self.client.delete(f'/api/v1/boards/{b.id}/members/{self.bob.id}/')
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BoardMembership.objects.filter(board=b, user=self.bob).exists())

    def test_invite_nonexistent_user_returns_404(self):
        self.auth(self.alice)
        b = Board.objects.create(owner=self.alice, name='X')
        r = self.client.post(f'/api/v1/boards/{b.id}/members/', {'username': 'noone'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    # --- Etiquetas ---

    def test_label_create_and_attach_to_card(self):
        self.auth(self.alice)
        b = Board.objects.create(owner=self.alice, name='B')
        col = Column.objects.create(board=b, title='X', order=0)
        lbl = self.client.post(
            f'/api/v1/boards/{b.id}/labels/', {'name': 'Bug', 'color': '#ef4444'}, format='json',
        ).data
        card = self.client.post(
            '/api/v1/tasks/', {'title': 'fix it', 'column': col.id, 'label_ids': [lbl['id']]}, format='json',
        ).data
        from tasks.models import Card
        self.assertEqual(list(Card.objects.get(pk=card['id']).labels.values_list('id', flat=True)), [lbl['id']])


class AuthAPITests(APITestCase):
    def test_register_login_me(self):
        r = self.client.post(
            '/api/v1/auth/register/',
            {'username': 'curro', 'email': 'c@example.com', 'password': 'currotfg2026'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        r = self.client.post(
            '/api/v1/auth/token/',
            {'username': 'curro', 'password': 'currotfg2026'}, format='json',
        )
        self.assertIn('access', r.data)

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['access'])
        r = self.client.get('/api/v1/auth/me/')
        self.assertEqual(r.data['username'], 'curro')

    def test_unauthenticated_request_rejected(self):
        self.assertEqual(self.client.get('/api/v1/boards/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='taken', password='pass1234')
        r = self.client.post(
            '/api/v1/auth/register/',
            {'username': 'taken', 'email': 't@example.com', 'password': 'goodpass1'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
