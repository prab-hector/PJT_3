from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class EditProfileViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester', password='secret123')

    def test_edit_profile_page_opens_for_user_without_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('edit_profile', args=[self.user.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/edit_profile.html')
