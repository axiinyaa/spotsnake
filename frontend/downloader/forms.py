from django import forms

class URLInputForm(forms.Form):
    url = forms.CharField(widget=forms.Textarea, label="", required=True)