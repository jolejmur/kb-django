# Generated by Django 5.2.2 on 2025-07-25 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitacionqr',
            name='vistas_qr',
            field=models.PositiveIntegerField(default=0, verbose_name='Vistas del QR'),
        ),
    ]
