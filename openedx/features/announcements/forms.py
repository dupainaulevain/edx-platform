"""
Forms for the Announcement Editor
"""

from django import forms

from .models import Announcement


class AnnouncementForm(forms.ModelForm):
    """
    Form for editing Announcements
    """
    content = forms.CharField(widget=forms.Textarea, label='')
    active = forms.BooleanField(initial=True)

    class Meta:
        model = Announcement
        fields = ['content', 'active']
