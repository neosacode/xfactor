# Generated by Django 2.0.1 on 2018-06-06 22:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0020_comissions_investment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='comissions',
            name='plan',
        ),
    ]
