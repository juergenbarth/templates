# Factur-X BT-85 Injector (OCA override)

## Zweck
Dieses Modul ergänzt die von OCA bereitgestellte Funktion  
`account_invoice_facturx.generate_facturx_xml` um die **Pflichtangabe des Kontoinhabers** (BT-85 / `AccountName`) im Factur-X (EN 16931) XML.

Ab Oktober 2025 verlangen viele Banken/Validatoren die Angabe des Kontoinhabers im SEPA-Kontext, obwohl das Feld in der Norm optional ist.  
Mit diesem Modul sind erzeugte Factur-X Rechnungen **konform** und zukunftssicher.

---

## Funktionsweise
- **Hook**: überschreibt `account.move.generate_facturx_xml`.  
- **Ablauf**:
  1. Originalfunktion von `account_invoice_facturx` wird aufgerufen → XML erzeugt.
  2. XML wird direkt nach der Erzeugung **gepatcht**:
     - XPath sucht nach `ram:PayeePartyCreditorFinancialAccount` (bzw. `CreditorFinancialAccount`).  
     - Falls dort kein `<ram:AccountName>` existiert oder der Inhalt leer ist → neues Element wird angelegt.  
  3. Der **Kontoinhaber-Name** wird eingefügt.

---

## Datenquelle für den Kontoinhaber
Die Funktion `_bt85_get_account_name()` zieht den Wert in folgender Reihenfolge:

1. `journal_id.bank_account_id.acc_holder_name`  
   → falls nicht befüllt: `journal_id.bank_account_id.partner_id.name`
2. Felder auf der Rechnung: `partner_bank_id`, `invoice_partner_bank_id`, `company_partner_bank_id`
3. Firmenname: `company_id.partner_id.name`

---

## Installation
1. Modul-Ordner `account_facturx_bt85_override_generate/` in den Odoo Addons-Pfad legen.
2. **Apps-Liste aktualisieren**.
3. Modul installieren (abhängig von `account_invoice_facturx`).

---

## Nutzung
- Erstelle eine Kundenrechnung und buche sie.
- Erzeuge das Factur-X PDF.
- Das eingebettete XML enthält nun unter:

```xml
<ram:PayeePartyCreditorFinancialAccount>
    <ram:IBANID>…</ram:IBANID>
    <ram:AccountName>Mein Firmenname</ram:AccountName>
</ram:PayeePartyCreditorFinancialAccount>
