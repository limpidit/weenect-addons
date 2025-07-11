
from odoo import models

import re


class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        # if self.body_html:
        #     self.body_html = re.sub('<[^<]+?>', '', self.body_html)
        return super()._send(auto_commit=auto_commit, raise_exception=raise_exception, smtp_session=smtp_session)
