from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from items.models import Item
from .models import SecurityProfile, CustodyRecord, ClaimRequest, HandoverLog


def make_user(username, email=None):
    return User.objects.create_user(
        username=username,
        email=email or f'{username}@test.com',
        password='pass123'
    )

def make_security_user(username):
    user = make_user(username, f'{username}@security.com')
    SecurityProfile.objects.create(user=user, badge_number=f'SEC-{username}')
    return user

def make_item(owner, item_type='found', status='active'):
    return Item.objects.create(
        title='Blue Backpack', description='Nike blue backpack with laptop',
        item_type=item_type, category='clothing',
        location='Library', date='2025-01-15', owner=owner, status=status
    )


class SecurityAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = make_user('student')
        self.officer = make_security_user('officer')

    def test_dashboard_requires_security(self):
        self.client.login(username='student', password='pass123')
        response = self.client.get(reverse('security:dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_accessible_to_security(self):
        self.client.login(username='officer', password='pass123')
        response = self.client.get(reverse('security:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access_dashboard(self):
        su = User.objects.create_superuser('admin', 'admin@test.com', 'pass123')
        self.client.login(username='admin', password='pass123')
        response = self.client.get(reverse('security:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirected_from_dashboard(self):
        response = self.client.get(reverse('security:dashboard'))
        self.assertRedirects(response, '/accounts/login/?next=/security/')


class CustodyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = make_user('student')
        self.officer = make_security_user('officer')
        self.item = make_item(self.student)

    def test_security_can_receive_item(self):
        self.client.login(username='officer', password='pass123')
        response = self.client.post(reverse('security:receive_item', args=[self.item.pk]), {
            'storage_location': 'Cabinet 2, Shelf A',
            'secret_identifiers': 'Serial: ABC123, red sticker on strap',
            'notes': 'Good condition',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustodyRecord.objects.filter(item=self.item).exists())

    def test_student_cannot_receive_item(self):
        self.client.login(username='student', password='pass123')
        response = self.client.post(reverse('security:receive_item', args=[self.item.pk]), {
            'storage_location': 'My house',
            'secret_identifiers': 'none',
        })
        self.assertEqual(response.status_code, 403)

    def test_duplicate_custody_prevented(self):
        self.client.login(username='officer', password='pass123')
        CustodyRecord.objects.create(item=self.item, received_by=self.officer, storage_location='Cabinet 1')
        response = self.client.post(reverse('security:receive_item', args=[self.item.pk]), {
            'storage_location': 'Cabinet 2',
            'secret_identifiers': 'test',
        })
        # Should redirect with a warning, not create a second custody record
        self.assertEqual(CustodyRecord.objects.filter(item=self.item).count(), 1)


class ClaimWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.finder = make_user('finder')
        self.claimant = make_user('claimant')
        self.officer = make_security_user('officer')
        self.item = make_item(self.finder)
        self.custody = CustodyRecord.objects.create(
            item=self.item, received_by=self.officer,
            storage_location='Cabinet 1',
            secret_identifiers='Serial: XYZ789, blue tag'
        )

    def test_student_can_submit_claim(self):
        self.client.login(username='claimant', password='pass123')
        response = self.client.post(reverse('security:submit_claim', args=[self.item.pk]), {
            'proof_description': 'Blue Nike backpack, 20L, black straps',
            'proof_identifiers': 'Serial XYZ789 on the bottom, blue tag with my name',
            'additional_notes': 'Lost near library on Monday',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClaimRequest.objects.filter(item=self.item, claimant=self.claimant).exists())
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.STATUS_CLAIMED)

    def test_finder_cannot_claim_own_report(self):
        self.client.login(username='finder', password='pass123')
        response = self.client.post(reverse('security:submit_claim', args=[self.item.pk]), {
            'proof_description': 'Test', 'proof_identifiers': 'Test',
        })
        self.assertFalse(ClaimRequest.objects.filter(item=self.item, claimant=self.finder).exists())

    def test_duplicate_claim_prevented(self):
        self.client.login(username='claimant', password='pass123')
        ClaimRequest.objects.create(
            item=self.item, claimant=self.claimant,
            proof_description='First claim', proof_identifiers='Test'
        )
        response = self.client.post(reverse('security:submit_claim', args=[self.item.pk]), {
            'proof_description': 'Second attempt', 'proof_identifiers': 'Test',
        })
        self.assertEqual(ClaimRequest.objects.filter(item=self.item, claimant=self.claimant).count(), 1)

    def test_security_can_approve_claim(self):
        claim = ClaimRequest.objects.create(
            item=self.item, claimant=self.claimant,
            proof_description='Blue Nike backpack', proof_identifiers='Serial XYZ789'
        )
        self.client.login(username='officer', password='pass123')
        response = self.client.post(reverse('security:review_claim', args=[claim.pk]), {
            'decision': 'approve',
            'security_notes': 'Identifiers match',
        })
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimRequest.STATUS_APPROVED)

    def test_security_can_reject_claim(self):
        claim = ClaimRequest.objects.create(
            item=self.item, claimant=self.claimant,
            proof_description='Vague description', proof_identifiers='None'
        )
        self.client.login(username='officer', password='pass123')
        response = self.client.post(reverse('security:review_claim', args=[claim.pk]), {
            'decision': 'reject',
            'rejection_reason': 'Description does not match item records.',
        })
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimRequest.STATUS_REJECTED)
        self.assertEqual(claim.rejection_reason, 'Description does not match item records.')
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.STATUS_ACTIVE)

    def test_rejection_requires_reason(self):
        claim = ClaimRequest.objects.create(
            item=self.item, claimant=self.claimant,
            proof_description='Test', proof_identifiers='Test'
        )
        self.client.login(username='officer', password='pass123')
        response = self.client.post(reverse('security:review_claim', args=[claim.pk]), {
            'decision': 'reject',
            'rejection_reason': '',  # Missing reason
        })
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimRequest.STATUS_PENDING)  # Not changed

    def test_student_cannot_review_claim(self):
        claim = ClaimRequest.objects.create(
            item=self.item, claimant=self.claimant,
            proof_description='Test', proof_identifiers='Test'
        )
        self.client.login(username='claimant', password='pass123')
        response = self.client.post(reverse('security:review_claim', args=[claim.pk]), {
            'decision': 'approve',
        })
        self.assertEqual(response.status_code, 403)


class HandoverTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.finder = make_user('finder')
        self.claimant = make_user('claimant')
        self.officer = make_security_user('officer')
        self.item = make_item(self.finder)
        self.custody = CustodyRecord.objects.create(
            item=self.item, received_by=self.officer, storage_location='Cabinet 1'
        )
        self.claim = ClaimRequest.objects.create(
            item=self.item, claimant=self.claimant,
            proof_description='Test', proof_identifiers='Test',
            status=ClaimRequest.STATUS_APPROVED,
            reviewed_by=self.officer
        )

    def test_security_can_record_handover(self):
        self.client.login(username='officer', password='pass123')
        response = self.client.post(reverse('security:process_handover', args=[self.claim.pk]), {
            'collector_name': 'John Claimant',
            'collector_id_number': 'STU/2024/001',
            'collector_id_type': 'student_id',
            'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(HandoverLog.objects.filter(claim=self.claim).exists())
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.STATUS_RESOLVED)

    def test_handover_requires_approved_claim(self):
        pending_claim = ClaimRequest.objects.create(
            item=self.item, claimant=self.finder,
            proof_description='Test', proof_identifiers='Test',
            status=ClaimRequest.STATUS_PENDING
        )
        self.client.login(username='officer', password='pass123')
        response = self.client.post(reverse('security:process_handover', args=[pending_claim.pk]), {
            'collector_name': 'Test', 'collector_id_number': '123', 'collector_id_type': 'student_id',
        })
        self.assertFalse(HandoverLog.objects.filter(claim=pending_claim).exists())
