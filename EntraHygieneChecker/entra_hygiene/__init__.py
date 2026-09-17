"""EntraHygieneChecker — read-only Microsoft Entra ID security hygiene CLI."""

__version__ = "1.0.0"

BANNER = """
========================================================================
  EntraHygieneChecker  v{version}
  AUTHORIZED TENANTS ONLY  |  READ-ONLY  |  NO WRITES
  Uses Microsoft Graph app-only (client credentials) access.
  Never grant this app write or RoleManagement.ReadWrite.* permissions.
========================================================================
""".format(version=__version__)
