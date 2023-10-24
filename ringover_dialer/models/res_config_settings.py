# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    # _description = 'Ringover dialer settings'

    ringover_dialer_tray_icon = fields.Boolean(string='Tray icon', default=False,
                                                    config_parameter='ringover_dialer.ringover_dialer_tray_icon')
    ringover_dialer_size = fields.Selection([
        ('big', 'Big'),
        ('medium', 'Medium'),
        ('small', 'Small')
    ], string='Dialer size', default='medium', config_parameter='ringover_dialer.ringover_dialer_size')
    ringover_dialer_position = fields.Selection([
        ('tr', 'Top right'),
        ('br', 'Bottom right'),
        ('bl', 'Bottom left'),
        ('tl', 'Top left'),
    ], string='Dialer position', default='br', config_parameter='ringover_dialer.ringover_dialer_position')

    @api.model
    def get_dialer_settings(self, param1=''):
        query = """SELECT \
        ringover_dialer_size as size, \
        ringover_dialer_position as position, \
        ringover_dialer_tray_icon as trayicon \
        from res_config_settings \
        order by create_date desc"""
        # self.env.cr.execute(query)
        self._cr.execute(query)
        result = self.env.cr.dictfetchone()
        print('result --->', result)
        return result
