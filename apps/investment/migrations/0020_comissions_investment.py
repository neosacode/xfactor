# Generated by Django 2.0.1 on 2018-06-06 21:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('investment', '0019_auto_20180606_1935'),
    ]

    operations = [
        migrations.AddField(
            model_name='comissions',
            name='investment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='comissions', to='investment.Investments'),
        ),
    ]