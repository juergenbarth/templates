from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    jklp_export_path = fields.Char(
        string="Export-Verzeichnis",
        config_parameter="jklp_invoice_fs_export.path",
        default="/mnt/paperless_consume",
        help="Ordner, in den Rechnungs-PDFs geschrieben werden."
    )
    jklp_on_post = fields.Boolean(
        string="Beim Buchen exportieren",
        config_parameter="jklp_invoice_fs_export.on_post",
        default=False
    )
    jklp_on_send = fields.Boolean(
        string="Beim Senden exportieren",
        config_parameter="jklp_invoice_fs_export.on_send",
        default=True
    )
    jklp_subdir_pattern = fields.Char(
        string="Unterordner-Muster",
        config_parameter="jklp_invoice_fs_export.subdir_pattern",
        help="z. B. {YYYY}-{MM}, {company}/{YYYY}, {partner}/{YYYY}-{MM}"
    )
    jklp_filename_pattern = fields.Char(
        string="Dateinamen-Muster",
        config_parameter="jklp_invoice_fs_export.filename_pattern",
        default="{invoice_number}",
        help="z. B. {invoice_number}_{date} oder {company}_{invoice_number}"
    )
    jklp_canary = fields.Boolean(
        string="Debug-Logs aktivieren",
        config_parameter="jklp_invoice_fs_export.canary",
        default=False
    )
