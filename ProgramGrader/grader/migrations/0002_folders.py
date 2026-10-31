import django.db.models.deletion
from django.db import migrations, models


def move_to_default_folder(apps, schema_editor):
    Exam = apps.get_model('grader', 'Exam')
    Folder = apps.get_model('grader', 'Folder')
    if Exam.objects.exists():
        folder = Folder.objects.get_or_create(name='未分類')[0]
        Exam.objects.update(folder=folder)


class Migration(migrations.Migration):

    dependencies = [
        ('grader', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='資料夾名稱')),
            ],
            options={'ordering': ['name']},
        ),
        migrations.AddField(
            model_name='exam',
            name='folder',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='exams', to='grader.folder', verbose_name='資料夾'),
        ),
        migrations.RunPython(move_to_default_folder, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='exam',
            name='folder',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='exams', to='grader.folder', verbose_name='資料夾'),
        ),
        migrations.AlterField(
            model_name='exam',
            name='name',
            field=models.CharField(max_length=100, verbose_name='考卷名稱'),
        ),
        migrations.AlterModelOptions(name='exam', options={'ordering': ['name']}),
        migrations.AlterUniqueTogether(name='exam', unique_together={('folder', 'name')}),
    ]
