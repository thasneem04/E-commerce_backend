from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password

from .models import Product, Category,Offer, CartItem, WishlistItem, CustomerProfile, Order, OrderItem, Enquiry
from .serializers import (
    ProductSerializer,
    CategorySerializer,
    OfferSerializer,
    CartItemSerializer,
    WishlistItemSerializer,
    CustomerProfileSerializer,
    OrderSerializer,
    EnquirySerializer,
)


# AUTH APIs (SESSION BASED)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"detail": "Username and password required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {"detail": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    allowed_usernames = set(getattr(settings, "SELLER_USERNAMES", []))
    is_seller = (
        user.is_staff
        or user.is_superuser
        or user.username in allowed_usernames
    )
    if not is_seller:
        return Response(
            {"detail": "Seller access required"},
            status=status.HTTP_403_FORBIDDEN
        )

    login(request, user)  # creates sessionid cookie
    request.session["is_seller"] = True

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    response = Response(
        {"message": "Login successful"},
        status=status.HTTP_200_OK
    )
    response.set_cookie(
        getattr(settings, "JWT_COOKIE_NAME", "access_token"),
        access_token,
        httponly=True,
        secure=getattr(settings, "JWT_COOKIE_SECURE", False),
        samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
        max_age=getattr(settings, "JWT_COOKIE_AGE_SECONDS", 60 * 60 * 24),
        path="/",
    )
    return response



@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    response = Response(
        {"message": "Logout successful"},
        status=status.HTTP_200_OK
    )
    response.delete_cookie(
        getattr(settings, "JWT_COOKIE_NAME", "access_token"),
        path="/"
    )
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def me_view(request):
    guard = _ensure_seller(request)
    if guard:
        return guard

    return Response(
        {
            "authenticated": True,
            "username": request.user.username,
        },
        status=status.HTTP_200_OK
    )


# CUSTOMER AUTH & PROFILE

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def customer_register(request):
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password")
    confirm_password = request.data.get("confirm_password")
    name = request.data.get("name", "")

    if not name or not email or not password or not confirm_password:
        return Response(
            {"detail": "All fields required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    if password != confirm_password:
        return Response(
            {"detail": "Passwords do not match"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(username=email).exists():
        return Response(
            {"detail": "User already exists"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name
    )
    CustomerProfile.objects.create(
        user=user,
        name=name,
        phone="",
        address="",
        city="",
        state="",
        pincode=""
    )

    return Response(
        {"message": "Registration successful"},
        status=status.HTTP_201_CREATED
    )


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def customer_login(request):
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"detail": "Email and password required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = User.objects.get(username=email)
    except User.DoesNotExist:
        return Response(
            {"detail": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if not check_password(password, user.password):
        return Response(
            {"detail": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    login(request, user)
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)

    response = Response(
        {
            "message": "Login successful",
            "user": {
                "email": user.email,
                "name": user.first_name,
            },
        },
        status=status.HTTP_200_OK
    )

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=60 * 60 * 24,
        path="/",
    )
    return response


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def customer_logout(request):
    logout(request)
    response = Response(
        {"message": "Logout successful"},
        status=status.HTTP_200_OK
    )
    response.delete_cookie("access_token", path="/")
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def customer_me(request):
    if not request.user.is_authenticated:
        return Response(
            {"authenticated": False},
            status=status.HTTP_200_OK
        )

    profile = getattr(request.user, "customer_profile", None)
    profile_complete = bool(profile and profile.is_complete())
    return Response(
        {
            "authenticated": True,
            "email": request.user.email,
            "name": request.user.first_name,
            "profile_complete": profile_complete,
        },
        status=status.HTTP_200_OK
    )


@api_view(["GET", "PUT"])
def customer_profile(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    profile, _ = CustomerProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "name": request.user.first_name or "",
            "phone": "",
            "address": "",
            "city": "",
            "state": "",
            "pincode": "",
        }
    )

    if request.method == "GET":
        serializer = CustomerProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = CustomerProfileSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _profile_complete(user):
    profile = getattr(user, "customer_profile", None)
    return bool(profile and profile.is_complete())


def _ensure_profile_complete(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if not _profile_complete(request.user):
        return Response(
            {"detail": "Profile incomplete"},
            status=status.HTTP_403_FORBIDDEN
        )
    return None




# CATEGORY APIs (READ)

@api_view(["GET", "POST"])
def category_list(request):
    if request.method == "GET":
        categories = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET", "POST"])
def product_list(request):

    # PUBLIC
    if request.method == "GET":
        category_value = request.query_params.get("category")
        products = Product.objects.filter(is_active=True)

        if category_value:
            category = Category.objects.filter(
                Q(slug__iexact=category_value) | Q(name__iexact=category_value)
            ).first()
            if category:
                products = products.filter(category=category)
            else:
                products = Product.objects.none()

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PROTECTED
    if request.method == "POST":
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data.copy()
        if "offer_price" in data and data.get("offer_price") in ("", None):
            data["offer_price"] = None

        serializer = ProductSerializer(data=data)
        if serializer.is_valid():
            serializer.save(seller=request.user)
            return Response(
                {"message": "Product created", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PUT", "DELETE"])
def product_detail(request, id):

    try:
        product = Product.objects.get(id=id)
    except Product.DoesNotExist:
        return Response(
            {"detail": "Product not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # PUBLIC
    if request.method == "GET":
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PROTECTED
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == "PUT":
        data = request.data.copy()
        if "offer_price" in data and data.get("offer_price") in ("", None):
            data["offer_price"] = None

        serializer = ProductSerializer(
            product, data=data, partial=True
        )
        if serializer.is_valid():
            if product.seller is None:
                serializer.save(seller=request.user)
            else:
                serializer.save()
            return Response(
                {"message": "Product updated", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        product.is_active = False
        product.save()
        return Response(
            {"message": "Product deleted"},
            status=status.HTTP_200_OK
        )
        
@api_view(["GET"])
def inactive_product_list(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    products = Product.objects.filter(is_active=False)
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(["GET"])
@permission_classes([AllowAny])
def related_products(request, category, id):
    category_obj = Category.objects.filter(
        Q(slug__iexact=category) | Q(name__iexact=category)
    ).first()

    if not category_obj:
        return Response([], status=status.HTTP_200_OK)

    products = Product.objects.filter(
        is_active=True,
        category=category_obj
    ).exclude(id=id)

    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
@api_view(["GET"])
@permission_classes([AllowAny])
def offer_list(request):
    offers = Offer.objects.filter(
        is_active=True,
        product__is_active=True
    )
    serializer = OfferSerializer(offers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
@api_view(["GET", "POST"])
def seller_offer_list(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method == "GET":
        offers = Offer.objects.all()
        serializer = OfferSerializer(offers, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        product_id = request.data.get("product")

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Invalid product"},
                status=status.HTTP_400_BAD_REQUEST
            )

        offer = Offer.objects.create(
            product=product,
            title=request.data.get("title"),
            subtitle=request.data.get("subtitle", ""),
            display_order=request.data.get("display_order", 0),
            is_active=request.data.get("is_active", True),
        )

        offer_price = request.data.get("offer_price")
        if offer_price not in (None, ""):
            try:
                offer_price_val = float(offer_price)
                if offer_price_val >= float(product.original_price):
                    return Response(
                        {"detail": "Offer price must be less than original price"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                product.offer_price = offer_price_val
                product.save()
            except ValueError:
                return Response(
                    {"detail": "Invalid offer price"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = OfferSerializer(offer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
def seller_offer_detail(request, id):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        offer = Offer.objects.get(id=id)
    except Offer.DoesNotExist:
        return Response(
            {"detail": "Offer not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        serializer = OfferSerializer(offer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "PUT":
        product_id = request.data.get("product")
        if product_id is not None:
            try:
                offer.product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return Response(
                    {"detail": "Invalid product"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if "title" in request.data:
            offer.title = request.data.get("title")
        if "subtitle" in request.data:
            offer.subtitle = request.data.get("subtitle", "")
        if "display_order" in request.data:
            offer.display_order = request.data.get("display_order", 0)
        if "is_active" in request.data:
            offer.is_active = request.data.get("is_active", True)

        offer.save()

        offer_price = request.data.get("offer_price")
        if offer_price not in (None, ""):
            try:
                offer_price_val = float(offer_price)
                if offer_price_val >= float(offer.product.original_price):
                    return Response(
                        {"detail": "Offer price must be less than original price"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                offer.product.offer_price = offer_price_val
                offer.product.save()
            except ValueError:
                return Response(
                    {"detail": "Invalid offer price"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = OfferSerializer(offer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "DELETE":
        offer.delete()
        return Response({"message": "Offer deleted"}, status=status.HTTP_200_OK)


# CART APIs

@api_view(["GET"])
def cart_list(request):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    items = CartItem.objects.filter(user=request.user).select_related(
        "product", "product__category"
    )
    serializer = CartItemSerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
def cart_add(request):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    product_id = request.data.get("product_id") or request.data.get("product")
    quantity = request.data.get("quantity", 1)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {"detail": "Invalid product"},
            status=status.HTTP_400_BAD_REQUEST
        )

    item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": quantity}
    )

    if not created:
        item.quantity += quantity
        item.save()

    serializer = CartItemSerializer(item)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["PUT"])
def cart_update(request):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    product_id = request.data.get("product_id") or request.data.get("product")
    quantity = request.data.get("quantity")

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response(
            {"detail": "Invalid quantity"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        item = CartItem.objects.get(user=request.user, product_id=product_id)
    except CartItem.DoesNotExist:
        return Response(
            {"detail": "Item not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if quantity <= 0:
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    item.quantity = quantity
    item.save()
    serializer = CartItemSerializer(item)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
def cart_remove(request, product_id):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    CartItem.objects.filter(user=request.user, product_id=product_id).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# WISHLIST APIs

@api_view(["GET"])
def wishlist_list(request):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    items = WishlistItem.objects.filter(user=request.user).select_related(
        "product", "product__category"
    )
    serializer = WishlistItemSerializer(items, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
def wishlist_add(request):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    product_id = request.data.get("product_id") or request.data.get("product")

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response(
            {"detail": "Invalid product"},
            status=status.HTTP_400_BAD_REQUEST
        )

    item, _ = WishlistItem.objects.get_or_create(
        user=request.user,
        product=product
    )
    serializer = WishlistItemSerializer(item)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
def wishlist_remove(request, product_id):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ORDER APIs

@api_view(["POST"])
def buy_now_order(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    product_id = request.data.get("product_id")
    quantity = request.data.get("quantity", 1)
    full_name = request.data.get("full_name")
    phone = request.data.get("phone")
    address1 = request.data.get("address1")
    address2 = request.data.get("address2", "")
    city = request.data.get("city")
    state = request.data.get("state")
    pincode = request.data.get("pincode")
    payment_method = request.data.get("payment_method")

    if not all([product_id, full_name, phone, address1, city, state, pincode, payment_method]):
        return Response(
            {"detail": "All required fields must be provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1
    if quantity < 1:
        quantity = 1

    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return Response(
            {"detail": "Invalid product"},
            status=status.HTTP_400_BAD_REQUEST
        )

    selling_price = product.offer_price if product.offer_price and product.offer_price < product.original_price else product.original_price
    total_amount = selling_price * quantity
    full_address = address1 if not address2 else f"{address1}, {address2}"

    order = Order.objects.create(
        user=request.user,
        full_name=full_name,
        phone=phone,
        address=full_address,
        city=city,
        state=state,
        pincode=pincode,
        total_amount=total_amount,
        status="placed",
    )

    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=quantity,
        price=selling_price,
    )

    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def order_from_cart(request):
    guard = _ensure_profile_complete(request)
    if guard:
        return guard

    full_name = request.data.get("full_name")
    phone = request.data.get("phone")
    address1 = request.data.get("address1")
    address2 = request.data.get("address2", "")
    city = request.data.get("city")
    state = request.data.get("state")
    pincode = request.data.get("pincode")
    payment_method = request.data.get("payment_method")

    if not all([full_name, phone, address1, city, state, pincode, payment_method]):
        return Response(
            {"detail": "All required fields must be provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    cart_items = CartItem.objects.filter(user=request.user).select_related("product")
    if not cart_items.exists():
        return Response(
            {"detail": "Cart is empty"},
            status=status.HTTP_400_BAD_REQUEST
        )

    full_address = address1 if not address2 else f"{address1}, {address2}"
    total_amount = 0
    order = Order.objects.create(
        user=request.user,
        full_name=full_name,
        phone=phone,
        address=full_address,
        city=city,
        state=state,
        pincode=pincode,
        total_amount=0,
        status="placed",
    )

    for item in cart_items:
        product = item.product
        selling_price = (
            product.offer_price
            if product.offer_price and product.offer_price < product.original_price
            else product.original_price
        )
        line_total = selling_price * item.quantity
        total_amount += line_total
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item.quantity,
            price=selling_price,
        )

    order.total_amount = total_amount
    order.save(update_fields=["total_amount"])
    cart_items.delete()

    order = Order.objects.prefetch_related("items", "items__product").get(id=order.id)
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def order_list(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    orders = Order.objects.filter(user=request.user).prefetch_related("items", "items__product")
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def order_detail(request, id):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        order = Order.objects.prefetch_related("items", "items__product").get(
            id=id, user=request.user
        )
    except Order.DoesNotExist:
        return Response(
            {"detail": "Order not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["PATCH"])
def order_cancel(request, id):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        order = Order.objects.get(id=id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"detail": "Order not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if order.status in ["delivered", "cancelled"]:
        return Response(
            {"detail": "Order cannot be cancelled"},
            status=status.HTTP_400_BAD_REQUEST
        )

    order.status = "cancelled"
    order.save(update_fields=["status"])
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)


# SELLER ORDER APIs

def _ensure_seller(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    allowed_usernames = set(getattr(settings, "SELLER_USERNAMES", []))
    if not (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.username in allowed_usernames
        or request.session.get("is_seller") is True
    ):
        return Response(
            {"detail": "Seller access required"},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


@api_view(["GET"])
def seller_order_list(request):
    guard = _ensure_seller(request)
    if guard:
        return guard

    allowed_usernames = set(getattr(settings, "SELLER_USERNAMES", []))
    is_seller_admin = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.username in allowed_usernames
    )

    if is_seller_admin:
        items = OrderItem.objects.select_related("order", "product").all()
    else:
        # Include unassigned products so dashboard can show orders
        # for legacy products created without a seller.
        items = OrderItem.objects.select_related(
            "order", "product"
        ).filter(Q(product__seller=request.user) | Q(product__seller__isnull=True))

    orders_map = {}
    for item in items:
        order = item.order
        if order.id not in orders_map:
            orders_map[order.id] = {
                "id": order.id,
                "user_id": order.user_id,
                "customer_name": order.full_name,
                "customer_email": getattr(order.user, "email", ""),
                "phone": order.phone,
                "address": f"{order.address}, {order.city}, {order.state} - {order.pincode}",
                "city": order.city,
                "state": order.state,
                "pincode": order.pincode,
                "total_amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at,
                "items": [],
            }
        orders_map[order.id]["items"].append({
            "product_id": item.product.id,
            "product_name": item.product.name,
            "category_name": item.product.category.name if item.product.category else "",
            "image": item.product.image.url if item.product.image else "",
            "quantity": item.quantity,
            "price": item.price,
            "line_total": item.price * item.quantity,
        })

    orders_list = list(orders_map.values())

    group_by = request.query_params.get("group")
    if group_by == "customer":
        customers_map = {}
        for order in orders_list:
            key = order.get("user_id") or order.get("customer_email") or order.get("phone")
            if key not in customers_map:
                customers_map[key] = {
                    "customer_id": order.get("user_id"),
                    "customer_name": order.get("customer_name"),
                    "customer_email": order.get("customer_email"),
                    "phone": order.get("phone"),
                    "total_orders": 0,
                    "total_value": 0,
                    "last_order_date": order.get("created_at"),
                    "orders": [],
                }

            customer = customers_map[key]
            customer["total_orders"] += 1
            customer["total_value"] += order.get("total_amount") or 0

            if customer["last_order_date"] and order.get("created_at"):
                if order["created_at"] > customer["last_order_date"]:
                    customer["last_order_date"] = order["created_at"]
            else:
                customer["last_order_date"] = order.get("created_at")

            customer["orders"].append(order)

        customers = list(customers_map.values())
        for customer in customers:
            customer["orders"].sort(
                key=lambda o: o.get("created_at").timestamp()
                if o.get("created_at")
                else 0,
                reverse=True
            )

        customers.sort(
            key=lambda c: c.get("last_order_date").timestamp()
            if c.get("last_order_date")
            else 0,
            reverse=True
        )

        return Response(customers, status=status.HTTP_200_OK)

    return Response(orders_list, status=status.HTTP_200_OK)


@api_view(["PATCH"])
def seller_order_status_update(request, order_id):
    guard = _ensure_seller(request)
    if guard:
        return guard

    status_value = request.data.get("status")
    allowed = ["placed", "shipped", "out_for_delivery", "delivered"]

    if status_value not in allowed:
        return Response(
            {"detail": "Invalid status"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {"detail": "Order not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # ensure seller owns at least one item in this order
    allowed_usernames = set(getattr(settings, "SELLER_USERNAMES", []))
    is_seller_admin = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.username in allowed_usernames
    )
    if not is_seller_admin:
        owns = OrderItem.objects.filter(
            Q(order=order) & (Q(product__seller=request.user) | Q(product__seller__isnull=True))
        ).exists()
        if not owns:
            return Response(
                {"detail": "Seller access required"},
                status=status.HTTP_403_FORBIDDEN
            )

    if order.status in ["delivered", "cancelled"]:
        return Response(
            {"detail": "Order cannot be updated"},
            status=status.HTTP_400_BAD_REQUEST
        )

    current_index = allowed.index(order.status) if order.status in allowed else 0
    new_index = allowed.index(status_value)
    if new_index < current_index:
        return Response(
            {"detail": "Invalid status transition"},
            status=status.HTTP_400_BAD_REQUEST
        )

    order.status = status_value
    order.save()

    return Response(
        {"message": "Status updated", "status": order.status},
        status=status.HTTP_200_OK
    )


# ENQUIRY APIs

@api_view(["POST"])
@permission_classes([AllowAny])
def enquiry_create(request):
    serializer = EnquirySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(
            user=request.user if request.user.is_authenticated else None
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def customer_enquiry_list(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    enquiries = Enquiry.objects.filter(user=request.user)
    serializer = EnquirySerializer(enquiries, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
def enquiry_list(request):
    guard = _ensure_seller(request)
    if guard:
        return guard

    enquiries = Enquiry.objects.all()
    serializer = EnquirySerializer(enquiries, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
