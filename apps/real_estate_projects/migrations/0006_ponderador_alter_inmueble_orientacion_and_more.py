# Generated by Django 5.2.3 on 2025-07-07 16:20

import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('real_estate_projects', '0005_remove_fase_disponible_comercializacion_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ponderador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(help_text="Nombre descriptivo del ponderador (ej: 'Avenida Principal', 'Vista al Mar', 'Piso Alto')", max_length=100)),
                ('porcentaje', models.DecimalField(decimal_places=2, help_text='Porcentaje de ajuste. Positivo aumenta precio, negativo lo reduce (ej: 15.00 = +15%, -5.00 = -5%)', max_digits=6, validators=[django.core.validators.MinValueValidator(Decimal('-100.00')), django.core.validators.MaxValueValidator(Decimal('500.00'))])),
                ('descripcion', models.TextField(blank=True, help_text='Descripción detallada del ponderador y cuándo aplicarlo')),
                ('activo', models.BooleanField(default=True, help_text='Determina si el ponderador está disponible para usar')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Ponderador de Precio',
                'verbose_name_plural': 'Ponderadores de Precio',
                'ordering': ['nombre'],
            },
        ),
        migrations.AlterField(
            model_name='inmueble',
            name='orientacion',
            field=models.CharField(blank=True, choices=[('calle', 'Calle'), ('avenida', 'Avenida')], max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='inmueble',
            name='ponderadores',
            field=models.ManyToManyField(blank=True, help_text='Ponderadores que afectan el precio de este inmueble', related_name='inmuebles', to='real_estate_projects.ponderador'),
        ),
    ]
