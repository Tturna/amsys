from django.conf import settings

def global_environment(request):
    return {
        "AMSYS_TRAEFIK_URL": settings.AMSYS_TRAEFIK_URL,
        "AMSYS_TITLE": settings.AMSYS_TITLE
    }
