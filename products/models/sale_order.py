from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError
import PyPDF2
import io, base64

class SaleOrder(models.Model):
    _inherit = "sale.order"
    sda_file=fields.Binary(string='TOPEC')
    proposition_commercial=fields.Binary(string='Proposition')

    marque_vehicule_vendu=fields.Char("Marque")
    genre_vehicule_vendu=fields.Char("Genre")
    modele_commercial=fields.Char("Modèle commercial")
    numero_affaire=fields.Char("Numéro d'affaire")
    

    
    def merge_pdf(self, sale_order_id=None):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        
        if sale_order_id is not None:
            saleOrder = self.env['sale.order'].browse(sale_order_id)
        else:
            saleOrdersIds = self.env.context.get("active_ids")
            saleOrder = self.env['sale.order'].browse(saleOrdersIds)[:1]
            # Génération du rapport de la commande de vente
            report = self.env['ir.actions.report']._get_report_from_name('sale.report_saleorder')
            reportOutput = report._render_qweb_pdf(report,saleOrder.id)[0]

        # Récupération des autres fichiers PDF
        template_bon_commande = self.env.ref('vehicules.bon_commande_attachment')
        sdaAttachment = saleOrder.sda_file
        propositionAttachment=saleOrder.proposition_commercial
        if not sdaAttachment:
            raise UserError("Impossible d'imprimer l'offre sans TOPEC")
        
        if not propositionAttachment:
            raise UserError("Impossible d'imprimer l'offre sans proposition commerciale")

        # Fusion des fichiers PDF
        #pdf_report = PyPDF2.PdfFileReader(io.BytesIO(reportOutput))
        pdf_0=PyPDF2.PdfFileReader(io.BytesIO(base64.b64decode(propositionAttachment)))
        pdf_1 = PyPDF2.PdfFileReader(io.BytesIO(base64.b64decode(sdaAttachment)))
        pdf_2 = PyPDF2.PdfFileReader(io.BytesIO(base64.b64decode(template_bon_commande.datas)))

        merged_pdf = PyPDF2.PdfFileWriter()
        for pdf in [pdf_0, pdf_1, pdf_2]:
            for page_num in range(len(pdf.pages)):
                merged_pdf.addPage(pdf.pages[page_num])

        output_stream = io.BytesIO()
        merged_pdf.write(output_stream)

        # Création de la pièce jointe
        new_attachment = self.env['ir.attachment'].create({
            "name": f"Devis_{saleOrder.id}.pdf",
            "datas": base64.b64encode(output_stream.getvalue()),
            "res_model": "sale.order",
            "res_id": saleOrder.id
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"{base_url}/web/content/{new_attachment.id}?download=true",
            "target": "new"
        }

    def action_quotation_send(self):
        self.ensure_one()

        # Générer le PDF fusionné
        merged_pdf = self.merge_pdf(self.id)

        # Créer un e-mail
        template = self.env.ref('sale.email_template_edi_sale')
        # Obtention du formulaire de composition d'e-mail pour l'affichage du wizard d'envoi d'e-mail
        compose_form = self.env.ref('mail.email_compose_message_wizard_form')

        # Création d'un dictionnaire de contexte pour passer des valeurs par défaut au wizard d'envoi d'e-mail
        ctx = {
            'default_model': 'sale.order',  # Modèle par défaut sur lequel l'e-mail sera basé
            'default_res_id': self.ids[0],  # ID de l'enregistrement par défaut sur lequel l'e-mail sera basé
            'default_use_template': bool(template),  # Indique si un modèle d'e-mail doit être utilisé
            'default_template_id': template.id,  # ID du modèle d'e-mail à utiliser
            'default_composition_mode': 'comment',  # Mode de composition de l'e-mail
            'mark_so_as_sent': True,  # Marquer le devis comme envoyé
            'custom_layout': "sale.mail_template_data_notification_email_sale_order",  # Layout personnalisé pour l'e-mail
            'force_email': True  # Forcer l'envoi d'e-mail
        }

        # Recherche de la pièce jointe originale (non fusionnée) associée à la commande
        original_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.id),
            ('name', 'not like', 'Devis_')], limit=1)

        # Si une pièce jointe originale est trouvée, la supprimer pour s'assurer que seul le PDF fusionné est attaché
        if original_attachment:
            original_attachment.unlink()

        # Recherche de la pièce jointe fusionnée pour l'attacher à l'e-mail
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.id),
            ('name', 'like', 'Devis_')], limit=1)

        # Si la pièce jointe fusionnée est trouvée, l'ajouter au contexte pour qu'elle soit attachée à l'e-mail
        if attachment:
            ctx['default_attachment_ids'] = [(6, 0, [attachment.id])]

        # Retourner une action pour ouvrir le wizard d'envoi d'e-mail avec le PDF fusionné attaché
        return {
            'name': _('Send Quotation'),  # Nom de l'action
            'type': 'ir.actions.act_window',  # Type d'action
            'view_mode': 'form',  # Mode d'affichage
            'res_model': 'mail.compose.message',  # Modèle de l'objet à afficher
            'views': [(compose_form.id, 'form')],  # Vue à utiliser
            'view_id': compose_form.id,  # ID de la vue
            'target': 'new',  # Ouvrir dans une nouvelle fenêtre
            'context': ctx,  # Contexte à passer au wizard
        }
