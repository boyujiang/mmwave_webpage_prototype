from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0005_alter_residentvitals_recorded_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='residentvitals',
            name='recorded_at',
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AddIndex(
            model_name='residentvitals',
            index=models.Index(
                fields=['resident', '-recorded_at'],
                name='analytics_r_residen_3a09b5_idx',
            ),
        ),
    ]
