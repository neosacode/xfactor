# Generated by Django 2.0.1 on 2018-05-20 15:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0007_auto_20180520_1539'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='investments',
            name='code',
        ),
    ]