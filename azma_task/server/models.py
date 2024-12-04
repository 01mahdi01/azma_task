from django.db import models
from django.contrib.postgres.indexes import GinIndex


class Logg(models.Model):
    json_recived = models.JSONField()
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            GinIndex(fields=['json_recived'])]