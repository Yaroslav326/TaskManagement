from .models import Session_counter


class CountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        url = request.path

        session, _ = Session_counter.objects.get_or_create(address_url=url)
        session.count += 1
        session.save()

        response = self.get_response(request)
        return response
