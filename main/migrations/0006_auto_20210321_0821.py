# Generated by Django 3.1.6 on 2021-03-21 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_team_tag'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='match_map',
            field=models.CharField(blank=True, default='Default Dust2', max_length=20),
        ),
        migrations.CreateModel(
            name='Server',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.IntegerField()),
                ('port', models.IntegerField(default=27015)),
                ('tournament', models.ManyToManyField(to='main.Tournament')),
            ],
        ),
    ]