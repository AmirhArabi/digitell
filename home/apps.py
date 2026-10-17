from django.apps import AppConfig


class HomeConfig(AppConfig):
    name = 'home'

    def ready(self):
        from utils.image_optimizer import register_image_compression_signals
        register_image_compression_signals()
