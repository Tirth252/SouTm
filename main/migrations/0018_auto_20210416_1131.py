# Generated by Django 3.1.6 on 2021-04-16 11:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_auto_20210413_1300'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournament',
            name='contact_no',
            field=models.BigIntegerField(null=True),
        ),
    ]