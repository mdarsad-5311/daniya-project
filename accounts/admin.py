from django.contrib import admin
from .models import NewsletterSubscriber


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('email',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

