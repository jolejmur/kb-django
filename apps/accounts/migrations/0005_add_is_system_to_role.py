# apps/accounts/migrations/0005_add_is_system_to_role.py

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_merge_20250617_2202'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='is_system',
            field=models.BooleanField(default=False),
        ),
    ]