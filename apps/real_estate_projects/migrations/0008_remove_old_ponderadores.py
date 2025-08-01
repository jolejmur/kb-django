# Generated by Django 5.2.3 on 2025-07-07 19:15

from django.db import migrations


def remove_global_ponderadores(apps, schema_editor):
    """Remove existing global ponderadores before making them project-specific"""
    Ponderador = apps.get_model('real_estate_projects', 'Ponderador')
    # Delete all existing ponderadores since they were global and now need to be project-specific
    Ponderador.objects.all().delete()


def reverse_remove_ponderadores(apps, schema_editor):
    """Reverse migration - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('real_estate_projects', '0007_remove_orientacion_field'),
    ]

    operations = [
        migrations.RunPython(remove_global_ponderadores, reverse_remove_ponderadores),
    ]
