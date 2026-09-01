from django.urls import path

from . import storefront_views as views

urlpatterns = [
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:item_id>/", views.cart_remove, name="cart_remove"),
    path("cart/discount/", views.cart_apply_discount, name="cart_apply_discount"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/pay/", views.order_pay, name="order_pay"),
    path("orders/<int:order_id>/cancel/", views.order_cancel, name="order_cancel"),
    path("payments/webhook/<slug:gateway>/", views.payment_webhook, name="payment_webhook"),
]
