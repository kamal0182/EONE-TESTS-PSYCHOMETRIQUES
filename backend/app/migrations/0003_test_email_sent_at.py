from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_test_current_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='email_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
