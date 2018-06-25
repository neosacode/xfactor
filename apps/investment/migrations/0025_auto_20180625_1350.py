# Generated by Django 2.0.1 on 2018-06-25 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0024_comissions_reinvestment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='investments',
            name='status_changed',
        ),
        migrations.AlterField(
            model_name='investments',
            name='status',
            field=models.CharField(choices=[('paid', 'paid'), ('consumed', 'consumed'), ('cancelled', 'cancelled')], default='paid', max_length=255),
        ),
    ]
