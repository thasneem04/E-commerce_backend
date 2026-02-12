import json

from rest_framework import serializers
from .models import Product, Category, Offer, ProductSizeVariant, CartItem, WishlistItem, CustomerProfile, Order, OrderItem, Enquiry
from django.utils import timezone
from datetime import timedelta


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSizeVariantSerializer(serializers.ModelSerializer):
    has_offer = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    selling_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductSizeVariant
        fields = [
            "id",
            "size_label",
            "original_price",
            "offer_price",
            "stock",
            "display_order",
            "is_active",
            "has_offer",
            "discount_percentage",
            "selling_price",
        ]

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
    size_variants = ProductSizeVariantSerializer(many=True, read_only=True)
    size_variants_payload = serializers.JSONField(write_only=True, required=False)
   
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
            "size_variants",
            "size_variants_payload",
        ]

    def _normalize_variants_payload(self):
        raw = self.initial_data.get("size_variants_payload", None)
        if raw is None:
            raw = self.initial_data.get("size_variants", None)
        if raw is None:
            return None

        if isinstance(raw, str):
            raw = raw.strip()
            if raw == "":
                return []
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError(
                    {"size_variants": "Invalid size variants format"}
                ) from exc

        if not isinstance(raw, list):
            raise serializers.ValidationError(
                {"size_variants": "Size variants must be a list"}
            )

        normalized = []
        for index, row in enumerate(raw):
            if not isinstance(row, dict):
                raise serializers.ValidationError(
                    {"size_variants": f"Variant #{index + 1} must be an object"}
                )

            size_label = str(row.get("size_label", "")).strip()
            if not size_label:
                raise serializers.ValidationError(
                    {"size_variants": f"Variant #{index + 1}: size is required"}
                )

            original_price = row.get("original_price")
            if original_price in (None, ""):
                raise serializers.ValidationError(
                    {"size_variants": f"Variant #{index + 1}: original price is required"}
                )

            offer_price = row.get("offer_price")
            stock = row.get("stock", 0)
            display_order = row.get("display_order", index)
            is_active = bool(row.get("is_active", True))

            try:
                original_price = float(original_price)
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    {"size_variants": f"Variant #{index + 1}: invalid original price"}
                ) from exc
            if original_price <= 0:
                raise serializers.ValidationError(
                    {"size_variants": f"Variant #{index + 1}: original price must be greater than zero"}
                )

            if offer_price in ("", None):
                offer_price = None
            else:
                try:
                    offer_price = float(offer_price)
                except (TypeError, ValueError) as exc:
                    raise serializers.ValidationError(
                        {"size_variants": f"Variant #{index + 1}: invalid offer price"}
                    ) from exc
                if offer_price <= 0 or offer_price >= original_price:
                    raise serializers.ValidationError(
                        {"size_variants": f"Variant #{index + 1}: offer price must be greater than zero and less than original price"}
                    )

            try:
                stock = int(stock)
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(
                    {"size_variants": f"Variant #{index + 1}: invalid stock"}
                ) from exc
            if stock < 0:
                raise serializers.ValidationError(
                    {"size_variants": f"Variant #{index + 1}: stock cannot be negative"}
                )

            try:
                display_order = int(display_order)
            except (TypeError, ValueError):
                display_order = index

            normalized.append(
                {
                    "size_label": size_label,
                    "original_price": original_price,
                    "offer_price": offer_price,
                    "stock": stock,
                    "display_order": display_order,
                    "is_active": is_active,
                }
            )

        seen = set()
        for row in normalized:
            key = row["size_label"].lower()
            if key in seen:
                raise serializers.ValidationError(
                    {"size_variants": "Duplicate size labels are not allowed"}
                )
            seen.add(key)

        return normalized

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs["_size_variants_payload"] = self._normalize_variants_payload()
        return attrs

    def _replace_size_variants(self, product, variants):
        product.size_variants.all().delete()
        if not variants:
            return
        ProductSizeVariant.objects.bulk_create(
            [
                ProductSizeVariant(
                    product=product,
                    size_label=row["size_label"],
                    original_price=row["original_price"],
                    offer_price=row["offer_price"],
                    stock=row["stock"],
                    display_order=row["display_order"],
                    is_active=row["is_active"],
                )
                for row in variants
            ]
        )

    def create(self, validated_data):
        variants = validated_data.pop("_size_variants_payload", None)
        validated_data.pop("size_variants_payload", None)
        product = super().create(validated_data)
        if variants is not None:
            self._replace_size_variants(product, variants)
        return product

    def update(self, instance, validated_data):
        variants = validated_data.pop("_size_variants_payload", None)
        validated_data.pop("size_variants_payload", None)
        product = super().update(instance, validated_data)
        if variants is not None:
            self._replace_size_variants(product, variants)
        return product

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
    original_price = serializers.SerializerMethodField()
    offer_price = serializers.SerializerMethodField()
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
            try:
                return obj.product.image.url
            except Exception:
                # Do not fail the whole offers API because of one broken image reference.
                return None
        return None

    def get_original_price(self, obj):
        try:
            return str(obj.product.original_price)
        except Exception:
            return None

    def get_offer_price(self, obj):
        try:
            value = obj.product.offer_price
            return None if value is None else str(value)
        except Exception:
            return None



class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    size_variant_id = serializers.SerializerMethodField()
    size_label = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    has_offer = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "size_variant_id",
            "size_label",
            "quantity",
            "price",
            "has_offer",
            "discounted_price",
        ]

    def _selected_original_price(self, obj):
        if obj.size_variant_id:
            return obj.size_variant.original_price
        return obj.product.original_price

    def _selected_offer_price(self, obj):
        if obj.size_variant_id:
            return obj.size_variant.offer_price
        return obj.product.offer_price

    def get_size_variant_id(self, obj):
        return obj.size_variant_id

    def get_size_label(self, obj):
        if obj.size_variant_id:
            return obj.size_variant.size_label
        return ""

    def get_price(self, obj):
        return self._selected_original_price(obj)

    def get_has_offer(self, obj):
        selected_offer = self._selected_offer_price(obj)
        selected_original = self._selected_original_price(obj)
        if selected_offer is None:
            return False
        try:
            return float(selected_offer) < float(selected_original)
        except (TypeError, ValueError):
            return False

    def get_discounted_price(self, obj):
        if not self.get_has_offer(obj):
            return None
        return self._selected_offer_price(obj)


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
        fields = ["id", "product", "product_name", "size_label", "quantity", "price"]


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
