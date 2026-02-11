from rest_framework import serializers
from .models import Product, Category,Offer, CartItem, WishlistItem, CustomerProfile, Order, OrderItem, Enquiry
from django.utils import timezone
from datetime import timedelta


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )
    seller = serializers.PrimaryKeyRelatedField(read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    has_offer = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    selling_price = serializers.SerializerMethodField()
   
    class Meta:
        model = Product
        fields = [
            "seller",
            "id",
            "category",
            "name",
            "slug",
            "original_price",
            "offer_price",
            "stock",
            "is_active",
            "featured",
            "image",
            "description",
            "created_at",
            "updated_at",
            "category_name",
            "has_offer",
            "discount_percentage",
            "selling_price",
        ]
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            data["image"] = instance.image.url
        return data


    def get_has_offer(self, obj):
        if obj.offer_price is None:
            return False
        try:
            offer = float(obj.offer_price)
            original = float(obj.original_price)
            if offer <= 0:
                return False
            return offer < original
        except (TypeError, ValueError):
            return False

    def get_discount_percentage(self, obj):
        if not self.get_has_offer(obj):
            return None
        try:
            original = float(obj.original_price)
            offer = float(obj.offer_price)
            if original <= 0:
                return None
            return round(((original - offer) / original) * 100)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    def get_selling_price(self, obj):
        if self.get_has_offer(obj):
            return obj.offer_price
        return obj.original_price
        
class OfferSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    original_price = serializers.DecimalField(
        source="product.original_price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    offer_price = serializers.DecimalField(
        source="product.offer_price",
        max_digits=10,
        decimal_places=2,
        allow_null=True,
        read_only=True
    )
    
    image = serializers.SerializerMethodField() 

    class Meta:
        model = Offer
        fields = [
            "id",
            "title",
            "subtitle",
            "product_id",
            "product_name",
            "original_price",
            "offer_price",
            "image",
            "display_order",
            "is_active",
        ]
    def get_image(self, obj):
        if obj.product and obj.product.image:
            return obj.product.image.url
        return None



class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    price = serializers.SerializerMethodField()
    has_offer = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "price", "has_offer", "discounted_price"]

    def get_price(self, obj):
        return obj.product.original_price

    def get_has_offer(self, obj):
        if obj.product.offer_price is None:
            return False
        try:
            return float(obj.product.offer_price) < float(obj.product.original_price)
        except (TypeError, ValueError):
            return False

    def get_discounted_price(self, obj):
        if not self.get_has_offer(obj):
            return None
        return obj.product.offer_price


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "added_at"]


class CustomerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            "email",
            "name",
            "phone",
            "address",
            "city",
            "state",
            "pincode",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    estimated_delivery_date = serializers.SerializerMethodField()
    remaining_days = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "full_name",
            "phone",
            "address",
            "city",
            "state",
            "pincode",
            "total_amount",
            "status",
            "created_at",
            "estimated_delivery_date",
            "remaining_days",
            "items",
        ]

    def get_estimated_delivery_date(self, obj):
        if obj.estimated_delivery_date:
            return obj.estimated_delivery_date
        if not obj.created_at:
            return None
        return (obj.created_at + timedelta(days=5)).date()

    def get_remaining_days(self, obj):
        est = self.get_estimated_delivery_date(obj)
        if not est:
            return None
        today = timezone.now().date()
        return max((est - today).days, 0)


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry
        fields = [
            "id",
            "name",
            "email",
            "subject",
            "order_id",
            "message",
            "created_at",
        ]
