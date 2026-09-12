from django.test import TestCase
from ..models import Product

class TestDashboard(TestCase):
    def test_dashboard_view(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'stockv/dashboard.html')
        
    def test_dashboard_includes_recent_products_list(self):
        # Create some test products
        Product.objects.create(name='Test Product 1', price=10.0)
        Product.objects.create(name='Test Product 2', price=20.0)

        response = self.client.get('/dashboard/')
        self.assertContains(response, 'Recent Products')
        self.assertContains(response, '<table class="recent-products">', html=True)
        