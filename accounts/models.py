from django.conf import settings
from django.db import models


class History(models.Model):
    IMPORT = 'import'
    EXPORT = 'export'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='histories')
    kind = models.CharField(max_length=8)
    file_name = models.CharField(max_length=255)
    detail = models.CharField(max_length=255, blank=True)
    lines = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
