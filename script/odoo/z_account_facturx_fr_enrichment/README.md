# z_facturx_fr_enrichment

Dieses Addon ergänzt CII-XML unmittelbar vor dem Einbetten in das PDF/A-3 (OCA account_invoice_facturx):

- BT-30: SIRET (14) oder SIREN (9) → SellerTradeParty/SpecifiedLegalOrganization/ID
- BT-85: Kontoname (acc_holder_name oder Firmenname) → Payee...FinancialAccount/Name
- BT-120: Nur ergänzen, wenn VAT Category = E und kein Grund vorhanden → "TVA non applicable, art. 293 B du CGI"

## Konfiguration
Einstellungen → Technisch → Konfiguration:
- Enrichment aktivieren/deaktivieren
- Logging aktivieren + Level (INFO/DEBUG)
- XML als Anhang vor/nach Anreicherung speichern
- Mail/Chatter-Meldung am Beleg bei Fehlern

## Hinweise
- `account_edi_ubl_cii` **deinstallieren**, wenn `account_invoice_facturx` genutzt wird.
- Validieren mit EN 16931/Peppol Schematron + veraPDF für PDF/A-3.