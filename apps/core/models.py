from django.db import models

# The core app doesn't need complex models for this implementation
# This is just a placeholder for future models

class CoreSettings(models.Model):
    """
    Model to store global settings for the application.
    """
    site_name = models.CharField(max_length=100, default="Django CRM")
    site_description = models.TextField(blank=True)
    maintenance_mode = models.BooleanField(default=False)
    
    # Ensure only one instance of this model exists
    class Meta:
        verbose_name = "Core Settings"
        verbose_name_plural = "Core Settings"
    
    def __str__(self):
        return self.site_name
    
    @classmethod
    def get_settings(cls):
        """Get or create the settings object"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings