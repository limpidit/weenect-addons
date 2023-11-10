from odoo import api,models, fields
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class FleetVehicleModel(models.Model):
    _inherit="fleet.vehicle.model"

    vehicle_type = fields.Selection(
        selection_add=[('camion', 'Camion')],default='camion',
        ondelete={'camion': 'set default'})

    @api.model
    def selection_remove(self):
        res = super(FleetVehicleModel, self).selection_remove()
        res.remove(('car', 'Car'))
        res.remove(('bike', 'Bike'))
        return res
