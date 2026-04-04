from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Item


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')

    def test_register_view_get(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_new_user(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser', 'first_name': 'New', 'last_name': 'User',
            'email': 'new@example.com', 'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_valid(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'testpass123'})
        self.assertRedirects(response, '/')

    def test_login_invalid(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)

    def test_create_item_requires_login(self):
        response = self.client.get(reverse('items:create'))
        self.assertRedirects(response, '/accounts/login/?next=/items/new/')


class ItemCreationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

    def test_create_lost_item(self):
        response = self.client.post(reverse('items:create'), {
            'title': 'Lost iPhone 13', 'description': 'Black iPhone with cracked screen',
            'item_type': 'lost', 'category': 'electronics', 'location': 'Library', 'date': '2025-01-15',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Item.objects.filter(title='Lost iPhone 13').exists())

    def test_create_found_item(self):
        response = self.client.post(reverse('items:create'), {
            'title': 'Found Blue Jacket', 'description': 'Blue denim jacket near canteen',
            'item_type': 'found', 'category': 'clothing', 'location': 'Canteen', 'date': '2025-01-15',
        })
        self.assertEqual(response.status_code, 302)
        item = Item.objects.get(title='Found Blue Jacket')
        self.assertEqual(item.owner, self.user)
        self.assertEqual(item.status, Item.STATUS_ACTIVE)

    def test_only_owner_can_edit(self):
        other = User.objects.create_user(username='other', password='pass123')
        item = Item.objects.create(title='T', description='T', item_type='lost', category='others', location='A', date='2025-01-15', owner=other)
        self.assertEqual(self.client.get(reverse('items:edit', args=[item.pk])).status_code, 403)

    def test_owner_can_resolve(self):
        item = Item.objects.create(title='My Item', description='T', item_type='lost', category='others', location='A', date='2025-01-15', owner=self.user)
        self.client.post(reverse('items:resolve', args=[item.pk]))
        item.refresh_from_db()
        self.assertEqual(item.status, Item.STATUS_RESOLVED)


class SearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='u', password='pass123')
        Item.objects.create(title='Red Backpack', description='Nike red backpack', item_type='lost', category='clothing', location='Lab', date='2025-01-01', owner=self.user)
        Item.objects.create(title='Blue Wallet', description='Leather wallet ID', item_type='found', category='documents', location='Canteen', date='2025-01-02', owner=self.user)
        Item.objects.create(title='iPhone charger', description='White USB-C charger', item_type='lost', category='electronics', location='Library', date='2025-01-03', owner=self.user)

    def test_search_by_title(self):
        response = self.client.get(reverse('items:list') + '?q=backpack')
        self.assertEqual(len(list(response.context['page_obj'])), 1)

    def test_search_by_description(self):
        response = self.client.get(reverse('items:list') + '?q=leather')
        self.assertEqual(len(list(response.context['page_obj'])), 1)

    def test_filter_by_type(self):
        response = self.client.get(reverse('items:list') + '?item_type=found')
        self.assertTrue(all(i.item_type == 'found' for i in response.context['page_obj']))

    def test_search_case_insensitive(self):
        response = self.client.get(reverse('items:list') + '?q=BACKPACK')
        self.assertEqual(len(list(response.context['page_obj'])), 1)


class MatchingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pass123')

    def _item(self, **kwargs):
        defaults = dict(description='Test', location='Lib', date='2025-01-01', owner=self.user)
        defaults.update(kwargs)
        return Item.objects.create(**defaults)

    def test_match_opposite_type_same_category(self):
        lost = self._item(title='Lost iPhone charger cable', item_type='lost', category='electronics')
        found = self._item(title='Found iPhone charger cable', item_type='found', category='electronics')
        self.assertIn(found, lost.get_matches())

    def test_no_match_same_type(self):
        lost1 = self._item(title='Lost charger cable', item_type='lost', category='electronics')
        lost2 = self._item(title='Lost charger cable phone', item_type='lost', category='electronics')
        self.assertNotIn(lost2, lost1.get_matches())

    def test_no_match_different_category(self):
        lost = self._item(title='Lost wallet', item_type='lost', category='documents')
        found = self._item(title='Found wallet', item_type='found', category='clothing')
        self.assertNotIn(found, lost.get_matches())

    def test_match_limit(self):
        lost = self._item(title='Lost red blue backpack bag sports', item_type='lost', category='clothing')
        for i in range(10):
            self._item(title=f'Found backpack bag sports {i}', item_type='found', category='clothing')
        self.assertLessEqual(len(lost.get_matches(limit=5)), 5)

    def test_resolved_excluded(self):
        lost = self._item(title='Lost phone charger', item_type='lost', category='electronics')
        found = self._item(title='Found phone charger', item_type='found', category='electronics', status=Item.STATUS_RESOLVED)
        self.assertNotIn(found, lost.get_matches())
