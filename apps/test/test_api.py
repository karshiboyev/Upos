from django.test import TestCase, Client
from django.urls import reverse

from apps.models import TestModel


class TestAPI(TestCase):
    def setUp(self):
        TestModel.objects.create(name="Test")
        TestModel.objects.create(name="Salom")
        self.client = Client()
        self.url = reverse("test-model")

    def test_url(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
