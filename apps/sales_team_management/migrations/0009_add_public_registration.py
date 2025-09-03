# Manual migration to add public registration field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_team_management', '0008_drop_legacy_tables'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationalunit',
            name='public_registration_enabled',
            field=models.BooleanField(
                default=False, 
                verbose_name='Registro Público Habilitado',
                help_text='Permite que los usuarios se auto-registren en esta unidad sin necesidad de login'
            ),
        ),
    ]