from django.apps import AppConfig


class RecommenderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recommender'
    verbose_name = '推荐系统'
