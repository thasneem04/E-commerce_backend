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
    seller_offer_detail
)
from . import views


urlpatterns = [
    # auth
    path("auth/login/", login_view),
    path("auth/logout/", logout_view),
    path("auth/me/", me_view),

    # categories
    path("categories/", category_list),

    # products
    path("products/", product_list),
    path("products/<int:id>/", product_detail),
    path("products/related/<str:category>/<int:id>/", views.related_products),
    path("products/inactive/", views.inactive_product_list),
    path("offers/", offer_list),                 # public
    path("seller/offers/", seller_offer_list),   # seller
    path("seller/offers/<int:id>/", seller_offer_detail),

    # customer auth/profile
    path("customer/register/", views.customer_register),
    path("customer/login/", views.customer_login),
    path("customer/logout/", views.customer_logout),
    path("customer/me/", views.customer_me),
    path("customer/profile/", views.customer_profile),

    # cart
    path("cart/", views.cart_list),
    path("cart/add/", views.cart_add),
    path("cart/update/", views.cart_update),
    path("cart/remove/<int:product_id>/", views.cart_remove),

    # wishlist
    path("wishlist/", views.wishlist_list),
    path("wishlist/add/", views.wishlist_add),
    path("wishlist/remove/<int:product_id>/", views.wishlist_remove),

    # orders
    path("orders/", views.order_list),
    path("orders/buy-now/", views.buy_now_order),
    path("orders/from-cart/", views.order_from_cart),
    path("orders/<int:id>/", views.order_detail),
    path("orders/<int:id>/cancel/", views.order_cancel),

    # seller orders
    path("seller/orders/", views.seller_order_list),
    path("seller/orders/<int:order_id>/status/", views.seller_order_status_update),

    # enquiry
    path("enquiry/", views.enquiry_create),
    path("customer/enquiries/", views.customer_enquiry_list),
    path("seller/enquiries/", views.enquiry_list),
]
