from django.urls import path
from .views import (
    product_list,
    product_detail,
    login_view,
    logout_view,
    me_view,
    category_list,
    offer_list,
    seller_offer_list,
    seller_offer_detail,
    csrf_token_view
    
)
from . import views

app_name = "products"

urlpatterns = [
    # auth
    path("csrf/", csrf_token_view, name="csrf"),
    path("auth/login/", login_view, name="auth-login"),
    path("auth/logout/", logout_view, name="auth-logout"),
    path("auth/me/", me_view, name="auth-me"),
    

    # categories
    path("categories/", category_list, name="categories"),

    # products
    path("products/", product_list, name="products"),
    path("products/<int:id>/", product_detail, name="product-detail"),
    path("products/related/<str:category>/<int:id>/", views.related_products, name="products-related"),
    path("products/inactive/", views.inactive_product_list, name="products-inactive"),
    path("offers/", offer_list, name="offers-public"),                 # public
    path("seller/offers/", seller_offer_list, name="seller-offers"),   # seller
    path("seller/offers/<int:id>/", seller_offer_detail, name="seller-offer-detail"),

    # customer auth/profile
    path("customer/register/", views.customer_register, name="customer-register"),
    path("customer/login/", views.customer_login, name="customer-login"),
    path("customer/logout/", views.customer_logout, name="customer-logout"),
    path("customer/me/", views.customer_me, name="customer-me"),
    path("customer/profile/", views.customer_profile, name="customer-profile"),

    # cart
    path("cart/", views.cart_list, name="cart"),
    path("cart/add/", views.cart_add, name="cart-add"),
    path("cart/update/", views.cart_update, name="cart-update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart-remove"),

    # wishlist
    path("wishlist/", views.wishlist_list, name="wishlist"),
    path("wishlist/add/", views.wishlist_add, name="wishlist-add"),
    path("wishlist/remove/<int:product_id>/", views.wishlist_remove, name="wishlist-remove"),

    # orders
    path("orders/", views.order_list, name="orders"),
    path("orders/buy-now/", views.buy_now_order, name="orders-buy-now"),
    path("orders/from-cart/", views.order_from_cart, name="orders-from-cart"),
    path("orders/<int:id>/", views.order_detail, name="order-detail"),
    path("orders/<int:id>/cancel/", views.order_cancel, name="order-cancel"),

    # seller orders
    path("seller/orders/", views.seller_order_list, name="seller-orders"),
    path("seller/orders/<int:order_id>/status/", views.seller_order_status_update, name="seller-order-status"),

    # enquiry
    path("enquiry/", views.enquiry_create, name="enquiry-create"),
    path("customer/enquiries/", views.customer_enquiry_list, name="customer-enquiries"),
    path("seller/enquiries/", views.enquiry_list, name="seller-enquiries"),
]
