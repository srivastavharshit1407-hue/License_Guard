from rest_framework.exceptions import PermissionDenied


class OrgScopedMixin:
    """
    Drop this into any ViewSet whose model inherits OrgOwnedModel.

    It does two things, and they are the whole of your multi-tenancy story:
      1. Filters every queryset down to the caller's organization.
      2. Stamps the caller's organization onto anything they create.

    Without this a user from Acme could read Globex's licences by guessing an
    ID, so never write an org-owned ViewSet without it.
    """

    def get_organization(self):
        org = getattr(self.request.user, "organization", None)
        if org is None:
            raise PermissionDenied("Your account is not linked to an organization.")
        return org

    def get_queryset(self):
        return super().get_queryset().filter(organization=self.get_organization())

    def perform_create(self, serializer):
        serializer.save(organization=self.get_organization())
