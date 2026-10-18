from django import forms

from .models import Customer, Interaction, Lead, Opportunity, Product, Quote, QuoteItem, SupportTicket, Task


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "email", "phone", "company", "source", "status", "interaction_notes"]
        widgets = {"interaction_notes": forms.Textarea(attrs={"rows": 3})}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        duplicate = Customer.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("Email này đã tồn tại trong hệ thống.")
        return email


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["name", "email", "phone", "source", "need"]
        widgets = {"need": forms.Textarea(attrs={"rows": 3})}


class InteractionForm(forms.ModelForm):
    class Meta:
        model = Interaction
        fields = ["customer", "type", "content", "happened_at"]
        widgets = {
            "happened_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "content": forms.Textarea(attrs={"rows": 3}),
        }


class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = ["customer", "name", "amount", "probability", "stage", "expected_close_date"]
        widgets = {"expected_close_date": forms.DateInput(attrs={"type": "date"})}


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "customer", "due_date", "priority", "notes"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "code", "unit", "price", "is_active", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ["customer", "opportunity", "code", "discount", "status", "valid_until", "notes"]
        widgets = {"valid_until": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 2})}


class QuoteItemForm(forms.ModelForm):
    class Meta:
        model = QuoteItem
        fields = ["quote", "product", "quantity", "unit_price"]


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ["customer", "title", "description", "category", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
