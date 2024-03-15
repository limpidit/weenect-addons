from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta




class SaleOrder(models.Model):
    _inherit = 'sale.order'

    imei_filled = fields.Boolean(string='IMEI enregistrés',store=True)

    @api.onchange('partner_id')
    def _onchange_partner_id_check_sav(self):
        if not self.partner_id:
            return
        
        new_lines = []
        messages = []

        traceurs_sav = self.env['traceurs.sav'].search([
            ('client_id', '=', self.partner_id.id),
            ('type', '=', 'sav'),
            ('traceur_sav_recu', '=', False),
        ])

        traceurs_sav_a_envoyer = self.env['traceurs.sav'].search([
            ('client_id', '=', self.partner_id.id),
            ('type', '=', 'sav'),
            ('traceur_sav_recu', '=', True),
            ('traceur_sav_a_envoyer', '=', True),
        ])

        for traceur in traceurs_sav_a_envoyer:
            # Préparation des valeurs pour la nouvelle ligne de commande
            line_vals = {
                'product_id': traceur.product_id.id,
                'name': traceur.product_id.display_name or '',
                'product_uom_qty': 1,
                'product_uom': traceur.product_id.uom_id.id,
                'price_unit': traceur.product_id.list_price,
                'traceur_sav': True,  # Supposition de l'existence de ce champ dans sale.order.line
            }
            # Ajout des valeurs préparées à la liste
            new_lines.append((0, 0, line_vals))

        # Affectation des nouvelles lignes à la commande (elles seront affichées dans le formulaire mais pas encore sauvegardées en base de données)
        if new_lines:
            self.order_line = new_lines

        if traceurs_sav_a_envoyer:
            message = _("Il y a un ou plusieurs traceurs SAV à envoyer. Ne pas oublier de les ajouter dans la commande.\n")
            for traceur in traceurs_sav_a_envoyer:
                product_name = traceur.product_id.name_get()[0][1] if traceur.product_id else _('Produit non spécifié')
                message += _("Produit : %s\n" % product_name)
            messages.append(message)
            
        if traceurs_sav:
            model_name = 'traceurs.sav'  # Assurez-vous que cela correspond au nom technique de votre modèle de traceur
            links = []
            for traceur in traceurs_sav:
                link = "<a href='#id={}&model={}' target='_blank'>{}</a>".format(traceur.id, model_name, traceur.imei or 'Traceur SAV')
                links.append(link)
            
            note = _('Vérifier le retour des traceurs SAV : ') + ', '.join(links)
            
            # Création d'une activité "A faire" pour le client, 8 jours plus tard
            date_deadline = fields.Date.today() + timedelta(days=8)
            
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'note': note,
                'res_id': self.partner_id.id,
                'res_model_id': self.env['ir.model']._get('res.partner').id,
                'date_deadline': date_deadline,
            })
            message = _("Il y a des traceurs SAV non retournés. Veuillez contacter votre client pour demander le retour.")
            messages.append(message)

                # Gestion des messages d'avertissement
        if messages:
            warning_message = ' '.join(messages)
            return {
                'warning': {
                    'title': _("Attention"),
                    'message': warning_message,
                }
            }
            
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        
        if 'state' in vals and vals['state'] == 'sale':  # ou une autre condition de confirmation de commande
            for order in self:
                # Pour chaque produit distinct dans les lignes où traceur_sav est coché
                produits_traceur_sav = order.order_line.filtered('traceur_sav').mapped('product_id')
                
                for produit in produits_traceur_sav:
                    # Compter uniquement les lignes de commande actives pour ce produit où traceur_sav est coché
                    nb_lignes_actives_traceur_sav = len(order.order_line.filtered(lambda l: l.traceur_sav and l.product_id == produit))
                    
                    # Trouver tous les traceurs SAV correspondants à envoyer pour ce produit
                    traceurs_sav_a_envoyer = self.env['traceurs.sav'].search([
                        ('client_id', '=', order.partner_id.id),
                        ('product_id', '=', produit.id),
                        ('type', '=', 'sav'),
                        ('traceur_sav_a_envoyer', '=', True),
                    ])
                    
                    if traceurs_sav_a_envoyer:
                        # S'assurer qu'on met à jour uniquement le nombre de traceurs correspondant au nombre de lignes actives
                        traceurs_a_mettre_a_jour = traceurs_sav_a_envoyer[:nb_lignes_actives_traceur_sav]
                        for traceur in traceurs_a_mettre_a_jour:
                            traceur.write({
                                'traceur_sav_a_envoyer': False,
                                'traceur_sav_termine': True,
                            })

        return res
