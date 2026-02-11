from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Offer, Product


class OfferApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.seller = User.objects.create_user(
            username="seller",
            password="pass12345",
            is_staff=True,
        )
        self.category = Category.objects.create(name="Cloth")

    def test_public_offers_returns_only_active_with_active_product(self):
        active_product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Shirt",
            original_price=500,
            offer_price=400,
            stock=5,
            is_active=True,
        )
        inactive_product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Old Shirt",
            original_price=500,
            offer_price=300,
            stock=5,
            is_active=False,
        )
        no_price_product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="No Price Offer",
            original_price=500,
            offer_price=None,
            stock=5,
            is_active=True,
        )

        visible_offer = Offer.objects.create(
            product=active_product,
            title="Mega Sale",
            is_active=True,
        )
        no_price_visible_offer = Offer.objects.create(
            product=no_price_product,
            title="Visible Without Discount",
            is_active=True,
        )
        Offer.objects.create(
            product=active_product,
            title="Inactive Offer",
            is_active=False,
        )
        Offer.objects.create(
            product=inactive_product,
            title="Hidden Product Offer",
            is_active=True,
        )
        response = self.client.get("/api/offers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item["id"] for item in response.data}
        self.assertIn(visible_offer.id, returned_ids)
        self.assertIn(no_price_visible_offer.id, returned_ids)

    def test_seller_offer_create_invalid_price_returns_400_without_creating_offer(self):
        product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Cooker",
            original_price=600,
            offer_price=None,
            stock=3,
            is_active=True,
        )
        self.client.force_login(self.seller)

        response = self.client.post(
            "/api/seller/offers/",
            {
                "title": "Bad Offer",
                "subtitle": "Too expensive",
                "product": product.id,
                "display_order": 1,
                "offer_price": "700",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Offer.objects.count(), 0)

        product.refresh_from_db()
        self.assertIsNone(product.offer_price)
