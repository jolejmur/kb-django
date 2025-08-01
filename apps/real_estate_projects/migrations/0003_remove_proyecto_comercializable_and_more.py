# Generated by Django 5.2.3 on 2025-07-04 19:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('real_estate_projects', '0002_remove_inmueble_precio_base_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='proyecto',
            name='comercializable',
        ),
        migrations.RemoveField(
            model_name='proyecto',
            name='fecha_fin',
        ),
        migrations.RemoveField(
            model_name='proyecto',
            name='fecha_inicio',
        ),
        migrations.RemoveField(
            model_name='proyecto',
            name='precio_desde',
        ),
        migrations.RemoveField(
            model_name='proyecto',
            name='precio_hasta',
        ),
        migrations.AlterField(
            model_name='proyecto',
            name='estado',
            field=models.CharField(choices=[('planificacion', 'Planificación'), ('desarrollo', 'En Desarrollo'), ('construccion', 'En Construcción'), ('finalizado', 'Finalizado'), ('cancelado', 'Cancelado')], default='planificacion', max_length=20),
        ),
        migrations.AlterField(
            model_name='proyecto',
            name='gerente_proyecto',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='proyectos', to='real_estate_projects.gerenteproyecto'),
        ),
    ]
