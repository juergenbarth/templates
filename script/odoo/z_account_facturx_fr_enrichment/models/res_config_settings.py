# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    xfx_enable = fields.Boolean(string="Enable Factur-X Enrichment", default=True,
        config_parameter="x_facturx_fr_enrichment.enable")
    xfx_logging_enable = fields.Boolean(string="Enable Enrichment Logging", default=False,
        config_parameter="x_facturx_fr_enrichment.logging_enable")
    xfx_logging_level = fields.Selection([
        ("INFO", "INFO"),
        ("DEBUG", "DEBUG"),
        ("WARNING", "WARNING"),
        ("ERROR", "ERROR"),
    ], string="Logging Level", default="INFO",
        config_parameter="x_facturx_fr_enrichment.logging_level")
    xfx_attach_snapshots = fields.Boolean(string="Attach XML snapshots (pre/post)", default=False,
        config_parameter="x_facturx_fr_enrichment.attach_snapshots")
    xfx_notify_chatter = fields.Boolean(string="Post chatter note on errors", default=True,
        config_parameter="x_facturx_fr_enrichment.notify_chatter")