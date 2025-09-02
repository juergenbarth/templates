{
    "name": "JKLP Invoice FS Export",
    "summary": "Exportiert Rechnungs-PDFs beim Buchen/Senden ins Filesystem",
    "version": "18.0.1.1.13",
    "author": "Jürgen Barth",
    "license": "LGPL-3",
    "depends": ["account", "mail"],
    "data": [
       "data/ir_config_parameter.xml",
       "views/res_config_settings_form.xml",   # NEU: Standalone-Form
       "views/settings_action_menu.xml",       # NEU: Action + Menü
    ],
    "application": False,
}
