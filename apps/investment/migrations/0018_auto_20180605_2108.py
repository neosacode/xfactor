# Generated by Django 2.0.1 on 2018-06-05 21:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0017_plans_membership_fee'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='incomes',
            unique_together={('investment', 'date')},
        ),
    ]