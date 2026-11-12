"""The inventory's URLs, below /lab/inventory/."""

from django.urls import path
from django.views.generic import RedirectView

from inventory import views

urlpatterns = [
    path("", RedirectView.as_view(url=views.LIST)),
    path("end-products/", views.item_list, name="item_list"),
    path("end-products/new/", views.item_new, name="item_new"),
    path("end-products/bulk/", views.lot_list, name="lot_list"),
    path("items/<int:pk>/", views.item_page, name="item"),
    path("items/<int:pk>/edit/", views.item_edit, name="item_edit"),
    path("items/<int:pk>/fill/", views.item_fill, name="item_fill"),
    path("items/<int:pk>/correct/", views.item_correct,
         name="item_correct"),
    path("items/<int:pk>/consumption/", views.item_consumption,
         name="item_consumption"),
    path("items/<int:pk>/movements/<int:movement>/reverse/",
         views.movement_reverse, name="movement_reverse"),
    path("deliveries/", views.note_list, name="note_list"),
    path("deliveries/new/", views.note_new, name="note_new"),
    path("deliveries/<int:pk>/", views.note_page, name="note"),
    path("deliveries/<int:pk>/edit/", views.note_edit, name="note_edit"),
    path("deliveries/<int:pk>/reverse/", views.note_reverse,
         name="note_reverse"),
    path("bulk/new/", views.lot_new, name="lot_new"),
    path("bulk/<int:pk>/", views.lot_page, name="lot"),
    path("bulk/<int:pk>/edit/", views.lot_edit, name="lot_edit"),
    path("bulk/<int:pk>/correct/", views.lot_correct, name="lot_correct"),
    path("bulk/<int:pk>/withdraw/", views.lot_withdraw,
         name="lot_withdraw"),
    path("bulk/movements/<int:pk>/reverse/", views.lot_movement_reverse,
         name="lot_movement_reverse"),
]
