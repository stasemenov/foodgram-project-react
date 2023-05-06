from csv import reader

from django.conf import settings
from django.core.management import BaseCommand

from recipes.models import Ingredient, Tag

DATA_PATH = str(settings.BASE_DIR)[:-7] + 'data/'

TABLES_DICT = {
    Tag: 'tags.csv',
    Ingredient: 'ingredients.csv',
}


class Command(BaseCommand):
    """Загрузка данных из csv-файлов"""

    def handle(self, *args, **options):
        for model, base in TABLES_DICT.items():
            with open(f'{DATA_PATH}{base}', 'r', encoding='utf-8') as csv_file:
                if model == Tag:
                    for tag, color, slug in reader(csv_file):
                        Tag.objects.get_or_create(
                            name=tag,
                            color=color,
                            slug=slug
                        )
                    print('Теги успешно загружены')

                else:
                    for name, unit in reader(csv_file):
                        Ingredient.objects.get_or_create(
                            name=name,
                            measurement_unit=unit
                        )
                    print('Игредиенты успешно загружены')
