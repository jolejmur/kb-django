# Generated by Django 5.2.2 on 2025-07-25 16:39

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EventoComercial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, verbose_name='Nombre del Evento')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('fecha_inicio', models.DateTimeField(verbose_name='Fecha y Hora de Inicio')),
                ('fecha_fin', models.DateTimeField(verbose_name='Fecha y Hora de Fin')),
                ('ubicacion', models.CharField(max_length=300, verbose_name='Ubicación')),
                ('activo', models.BooleanField(default=True, verbose_name='Evento Activo')),
                ('permite_invitaciones', models.BooleanField(default=True, verbose_name='Permitir Invitaciones')),
                ('requiere_registro_cliente', models.BooleanField(default=True, verbose_name='Requiere Registro de Cliente')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='Última Actualización')),
                ('creado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
            ],
            options={
                'verbose_name': 'Evento Comercial',
                'verbose_name_plural': 'Eventos Comerciales',
                'ordering': ['-fecha_inicio'],
                'permissions': [('view_evento_reports', 'Can view event reports'), ('manage_eventos', 'Can manage all events')],
            },
        ),
        migrations.CreateModel(
            name='EstadisticaEvento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_invitaciones', models.PositiveIntegerField(default=0)),
                ('total_visitas', models.PositiveIntegerField(default=0)),
                ('total_clientes_unicos', models.PositiveIntegerField(default=0)),
                ('estadisticas_vendedores', models.JSONField(blank=True, default=dict)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('evento', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='estadisticas', to='events.eventocomercial', verbose_name='Evento')),
            ],
            options={
                'verbose_name': 'Estadística de Evento',
                'verbose_name_plural': 'Estadísticas de Eventos',
            },
        ),
        migrations.CreateModel(
            name='InvitacionQR',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_qr', models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Código QR')),
                ('activa', models.BooleanField(default=True, verbose_name='Invitación Activa')),
                ('usos_maximos', models.PositiveIntegerField(default=1, verbose_name='Usos Máximos')),
                ('usos_actuales', models.PositiveIntegerField(default=0, verbose_name='Usos Actuales')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')),
                ('fecha_expiracion', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de Expiración')),
                ('archivo_qr', models.ImageField(blank=True, null=True, upload_to='qr_codes/', verbose_name='Archivo QR')),
                ('evento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitaciones', to='events.eventocomercial', verbose_name='Evento')),
                ('vendedor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitaciones_generadas', to=settings.AUTH_USER_MODEL, verbose_name='Vendedor')),
            ],
            options={
                'verbose_name': 'Invitación QR',
                'verbose_name_plural': 'Invitaciones QR',
                'ordering': ['-fecha_creacion'],
                'unique_together': {('evento', 'vendedor')},
            },
        ),
        migrations.CreateModel(
            name='VisitaEvento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_cliente', models.CharField(max_length=200, verbose_name='Nombre del Cliente')),
                ('cedula_cliente', models.CharField(max_length=20, verbose_name='Cédula del Cliente')),
                ('telefono_cliente', models.CharField(max_length=20, verbose_name='Teléfono del Cliente')),
                ('email_cliente', models.EmailField(blank=True, max_length=254, verbose_name='Email del Cliente')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('fecha_visita', models.DateTimeField(auto_now_add=True, verbose_name='Fecha y Hora de Visita')),
                ('estado', models.CharField(choices=[('registrado', 'Registrado'), ('atendido', 'Atendido'), ('interesado', 'Interesado'), ('no_interesado', 'No Interesado'), ('seguimiento', 'En Seguimiento')], default='registrado', max_length=20, verbose_name='Estado')),
                ('invitacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='visitas', to='events.invitacionqr', verbose_name='Invitación QR')),
                ('registrado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='visitas_registradas', to=settings.AUTH_USER_MODEL, verbose_name='Registrado por')),
            ],
            options={
                'verbose_name': 'Visita a Evento',
                'verbose_name_plural': 'Visitas a Eventos',
                'ordering': ['-fecha_visita'],
                'unique_together': {('invitacion', 'cedula_cliente')},
            },
        ),
    ]
