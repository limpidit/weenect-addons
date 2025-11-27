
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _search_picking_for_assignation_domain(self):

        domain = super()._search_picking_for_assignation_domain()

        move = self[:1]
        rule = move.rule_id
        if rule and rule.separate_push_transfers:
            return [('id', '=', 0)]

        return domain
