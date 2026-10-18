from wagtail.models import Page
from django.shortcuts import redirect

class HomePage(Page):
    pass

class CustomerDashboardPage(Page):
    def serve(self, request):
        return redirect("crm:dashboard")