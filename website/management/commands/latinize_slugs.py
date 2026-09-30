"""Transliterate existing Cyrillic page slugs to Latin.

    python manage.py latinize_slugs            # dry run: show what would change
    python manage.py latinize_slugs --apply    # rename

Page.save() updates url_path and fires page_slug_changed, so Wagtail
(WAGTAILREDIRECTS_AUTO_CREATE) creates a 301 from every old Cyrillic URL —
links already shared in chats and socials keep working. Stored revisions are
patched too, so publishing an older draft does not bring the old slug back.
Idempotent: pages with ASCII slugs are skipped.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Page

from website.slugs import latin_slug


class Command(BaseCommand):
    help = 'Transliterate non-ASCII page slugs to Latin (with automatic redirects).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Actually rename (default is a dry run).')

    def handle(self, *args, apply=False, **options):
        pages = [p for p in Page.objects.all().order_by('path') if not p.slug.isascii()]
        if not pages:
            self.stdout.write('All slugs are already Latin.')
            return

        for page in pages:
            page = page.specific
            new_slug = self._unique_slug(page, latin_slug(page.slug) or f'page-{page.id}')
            self.stdout.write(f'{page.url_path}  ->  {new_slug}')
            if not apply:
                continue
            with transaction.atomic():
                old_slug = page.slug
                page.slug = new_slug
                page.save(clean=False, update_fields=['slug', 'url_path'])
                for revision in page.revisions.all():
                    if revision.content.get('slug') == old_slug:
                        revision.content['slug'] = new_slug
                        revision.save(update_fields=['content'])

        if not apply:
            self.stdout.write(self.style.WARNING('Dry run. Re-run with --apply to rename.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Renamed {len(pages)} page(s); redirects from old URLs created.'))

    @staticmethod
    def _unique_slug(page, base):
        siblings = page.get_siblings(inclusive=False)
        slug, n = base, 2
        while siblings.filter(slug=slug).exists():
            slug, n = f'{base}-{n}', n + 1
        return slug
