# Generated migration to update field references from legacy models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('real_estate_projects', '0011_alter_ponderador_options_and_more'),
        ('sales_team_management', '0008_drop_legacy_tables'),
    ]

    operations = [
        # First, rename the field in AsignacionEquipoProyecto
        migrations.RenameField(
            model_name='asignacionequipoproyecto',
            old_name='equipo_venta',
            new_name='organizational_unit',
        ),
        # Update the foreign key reference
        migrations.AlterField(
            model_name='asignacionequipoproyecto',
            name='organizational_unit',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                to='sales_team_management.organizationalunit'
            ),
        ),
        # Update the unique_together constraint
        migrations.AlterUniqueTogether(
            name='asignacionequipoproyecto',
            unique_together={('proyecto', 'organizational_unit')},
        ),
    ]