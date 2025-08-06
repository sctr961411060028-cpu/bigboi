from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _filter_aml_lot_valuation(self):
        # EXTENDS account
        return super()._filter_aml_lot_valuation() and not self.move_id.l10n_mx_edi_cfdi_cancel_id
