# Generated by Django 2.0.1 on 2018-05-09 19:18

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0002_auto_20180406_1213'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='graduations',
            options={'verbose_name': 'Graduation', 'verbose_name_plural': 'Graduations'},
        ),
        migrations.RemoveField(
            model_name='plangraceperiods',
            name='daily_income',
        ),
        migrations.AddField(
            model_name='plangraceperiods',
            name='income_percent',
            field=models.DecimalField(decimal_places=8, default=Decimal('0.00'), max_digits=20, verbose_name='Income percent'),
        ),
        migrations.AddField(
            model_name='plangraceperiods',
            name='payment_type',
            field=models.CharField(choices=[('daily', 'daily'), ('monthly', 'monthly')], default='monthly', max_length=20),
        ),
    ]