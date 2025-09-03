# Generated migration to rename M2M field in Proyecto
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('real_estate_projects', '0012_update_field_references'),
        ('sales_team_management', '0008_drop_legacy_tables'),
    ]

    operations = [
        # Rename the M2M field
        migrations.RenameField(
            model_name='proyecto',
            old_name='equipos_venta',
            new_name='organizational_units',
        ),
        # Update the M2M field reference
        migrations.AlterField(
            model_name='proyecto',
            name='organizational_units',
            field=models.ManyToManyField(
                related_name='proyectos',
                through='real_estate_projects.AsignacionEquipoProyecto',
                to='sales_team_management.organizationalunit'
            ),
        ),
    ]