# Generated by Django 2.1 on 2018-09-28 16:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('card', '0006_auto_20180810_1906'),
    ]

    operations = [
        migrations.AddField(
            model_name='recharges',
            name='is_paid',
            field=models.BooleanField(default=False, help_text='Mark this if the rechard has been paid', verbose_name='Is paid'),
        ),
    ]