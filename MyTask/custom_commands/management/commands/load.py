from django.core.management.base import BaseCommand
from django.urls import get_resolver
import multiprocessing as mp
import requests


def get_all_urls():
    resolver = get_resolver()
    urls = []

    def recurse_patterns(patterns, prefix='http://localhost:8000/'):
        for i in patterns:
            if hasattr(i, 'url_patterns'):
                new_prefix = prefix + str(i.pattern)
                recurse_patterns(i.url_patterns, new_prefix)
            else:
                url = prefix + str(i.pattern)
                urls.append(url)

    recurse_patterns(resolver.url_patterns)
    return sorted(set(urls))


def http_get(url):
    try:
        response = requests.get(url, timeout=5)
        return {
            'status_code': response.status_code,
            'url': url,
            'error': None
        }
    except Exception as e:
        return {
            'status_code': None,
            'url': url,
            'error': str(e)
        }


class Command(BaseCommand):

    def handle(self, *args, **options):
        workloads = range(1, mp.cpu_count() + 1)

        for processes in workloads:
            self.stdout.write(f"Тест: {processes} процессов")

            urls = get_all_urls()

            with mp.Pool(processes) as pool:
                results = pool.map(http_get, urls)

            successes = [r for r in results if r['error'] is None and r['status_code'] == 200]
            failures = [r for r in results if r['error'] is not None or r['status_code'] != 200]

            self.stdout.write(
                self.style.SUCCESS(f"Успешно: {len(successes)}")
            )
            self.stdout.write(
                self.style.ERROR(f"Ошибок: {len(failures)}")
            )

        self.stdout.write(self.style.MIGRATE_HEADING("Тест завершён"))

