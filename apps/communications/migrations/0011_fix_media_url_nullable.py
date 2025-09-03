# Generated manually to fix media_url nullable constraint

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0010_add_contacts_message_type'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE communications_mensaje ALTER COLUMN media_url DROP NOT NULL;",
            reverse_sql="ALTER TABLE communications_mensaje ALTER COLUMN media_url SET NOT NULL;"
        ),
    ]