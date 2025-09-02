# -*- coding: utf-8 -*-
{
    "name": "z_account_facturx_fr_enrichment",
    "summary": "Factur-X (CII) Enrichment for FR: BT-30 (SIRET/SIREN), BT-85 (Account Name), fallback BT-120; debug logging & attachments.",
    "version": "18.0.1.0.16",
    "author": "Juergen Barth",
    "website": "https://navigio.io",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": [
        "account_invoice_facturx",  # OCA
        "base_facturx",            # OCA core helpers
        "l10n_fr",                  # SIRET/SIREN Felder
    ],
    "data": [
        "data/ir_config_parameter.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
}