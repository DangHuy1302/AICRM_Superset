from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("customers/add/", views.create_customer, name="customer_add"),
    path("leads/add/", views.create_lead, name="lead_add"),
    path("interactions/add/", views.create_interaction, name="interaction_add"),
    path("opportunities/add/", views.create_opportunity, name="opportunity_add"),
    path("tasks/add/", views.create_task, name="task_add"),
    path("tasks/<int:task_id>/status/", views.update_task, name="task_status"),
    path("products/add/", views.create_product, name="product_add"),
    path("quotes/add/", views.create_quote, name="quote_add"),
    path("quote-items/add/", views.create_quote_item, name="quote_item_add"),
    path("tickets/add/", views.create_ticket, name="ticket_add"),
    path("tickets/<int:ticket_id>/status/", views.update_ticket, name="ticket_status"),
    path("customers/export/", views.export_customers, name="customer_export"),
    path("customers/<int:customer_id>/edit/", views.edit_customer, name="customer_edit"),
    path("customers/<int:customer_id>/delete/", views.delete_customer, name="customer_delete"),
    path("leads/<int:lead_id>/convert/", views.convert_lead, name="lead_convert"),
]
