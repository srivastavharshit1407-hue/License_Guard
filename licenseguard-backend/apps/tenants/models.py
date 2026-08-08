from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Every table gets created_at / updated_at for free."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(TimeStampedModel):
    """
    A tenant. Today you will have exactly one (your own company), but every
    other table carries an `organization` foreign key, so opening LicenseGuard
    up to other customers later is a config change, not a rewrite.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    primary_domain = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. acme.com - used to auto-join Google SSO users to this org.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "org"
            slug, counter = base, 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)


class OrgOwnedModel(TimeStampedModel):
    """Base class for anything that belongs to a tenant."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="%(class)ss"
    )

    class Meta:
        abstract = True
