# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, sql_db, _
from odoo.tools.mimetypes import guess_mimetype
import requests
import json
import base64
from datetime import datetime
import time
import html2text
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_link(self):
        for inv in self:
            base_url = inv.get_base_url()
            share_url = inv._get_share_url(redirect=True, signup_partner=True)
            url = base_url + share_url
            return url

    def _get_whatsapp_server(self):
        WhatsappServer = self.env['ir.whatsapp_server']
        whatsapp_ids = WhatsappServer.search([('status','=','authenticated')], order='sequence asc', limit=1)
        if whatsapp_ids:
            return whatsapp_ids
        return False
            
    def format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = self.env['res.lang']._lang_get(self.env.context.get('lang') or 'en_US')
 
        formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True)\
            .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')
 
        pre = post = u''
        if currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')
 
        return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

    def send_whatsapp_automatic(self):
        #if any(not move.is_invoice(include_receipts=True) for move in self):
        for inv in self.filtered(lambda i: i.is_invoice(include_receipts=True)):
            #print ('iiii',inv.state)
            new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
            MailMessage = self.env['mail.message']
            WhatsappComposeMessage = self.env['whatsapp.compose.message']
            Attachment = self.env['ir.attachment']
            if inv.payment_state == 'paid':
                template_id = self.env.ref('aos_whatsapp_account.invoice_paid_status', raise_if_not_found=False)
            else:
                template_id = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
            #print ('-template_id--',template_id)
            if self._get_whatsapp_server() and self._get_whatsapp_server().status == 'authenticated':
                KlikApi = self._get_whatsapp_server().klikapi()      
                KlikApi.auth()          
                template = template_id.generate_email(inv.id, ['body_html'])
                #print ('---invoice_paid_status---',template)
                body = template.get('body_html')
                subject = template.get('subject') or inv.name
                try:
                    body = body.replace('_PARTNER_', inv.partner_id.name)
                except:
                    _logger.warning('Failed to send Message to WhatsApp number %s', inv.partner_id.whatsapp)
                attachment_ids = []
                chatIDs = []
                message_data = {}
                send_message = {}
                status = 'error'
                partners = self.env['res.partner']          
                if inv.partner_id:
                    partners = inv.partner_id
                    # if inv.partner_id.child_ids:
                    #     #ADDED CHILD FROM PARTNER
                    #     for partner in inv.partner_id.child_ids:
                    #         partners += partner
                # is_exists = self.env['ir.attachment']
                res_name = inv.name.replace('/', '_')
                # domain = [('res_id', '=', inv.id), ('name', 'like', res_name + '%'), ('res_model', '=', 'account.move')] 
                is_attachment_exists = Attachment.search([('res_id', '=', inv.id), ('name', 'like', res_name + '%'), ('res_model', '=', 'account.move')], limit=1)# if len(active_ids) == 1 else is_exists
                #print ('==is_attachment_exists==',is_attachment_exists)
                if is_attachment_exists:
                    attachment_ids = is_attachment_exists
                # if not is_attachment_exists:

                #     attachments = []
                #     report = template_id.report_template
                #     print ('=report===',template_id,report,report.report_name)
                #     report_service = report.report_name

                #     if report.report_type not in ['qweb-html', 'qweb-pdf']:
                #         raise UserError(_('Unsupported report type %s found.') % report.report_type)
                #     res, format = report._render_qweb_pdf([inv.id])
                #     res = base64.b64encode(res)
                #     if not res_name:
                #         res_name = 'report.' + report_service
                #     ext = "." + format
                #     if not res_name.endswith(ext):
                #         res_name += ext
                #     attachments.append((res_name, res))

                #     for attachment in attachments:
                #         attachment_data = {
                #             'name': attachment[0],
                #             'store_fname': attachment[0],
                #             'datas': attachment[1],
                #             'type': 'binary',
                #             'res_model': 'account.move',
                #             'res_id': inv.id,
                #         }
                #         is_exists += Attachment.create(attachment_data)
                # else:
                #     is_exists += is_attachment_exists
                #rec.attachment_ids
                # attachment_ids = is_exists.ids#[(6, 0, is_exists.ids)] if is_exists else []
                for partner in partners:
                    if partner.whatsapp:
                        #SEND MESSAGE
                        if not attachment_ids:
                            whatsapp = partner._formatting_mobile_number()
                            message_data = {
                                'method': 'sendMessage',
                                'phone': whatsapp,
                                'body': html2text.html2text(body) + inv.get_link(),
                                'origin': inv.name,
                                'link': inv.get_link(),
                            }
                            if partner.chat_id:
                                message_data.update({'chatId': partner.chat_id, 'phone': '', 'origin': inv.name, 'link': inv.get_link()})
                            data_message = json.dumps(message_data)
                            send_message = KlikApi.post_request(method='sendMessage', data=data_message)
                            if send_message.get('message')['sent']:
                                chatID = send_message.get('chatID')
                                status = 'send'
                                partner.chat_id = chatID
                                chatIDs.append(chatID)
                                _logger.warning('Success to send Message to WhatsApp number %s', whatsapp)
                            else:
                                status = 'error'
                                _logger.warning('Failed to send Message to WhatsApp number %s', whatsapp)
                            new_cr.commit()
                        elif attachment_ids:
                            #print ('====attachment_ids===',attachment_ids.name)
                            status = 'pending'
                            whatsapp = partner._formatting_mobile_number()
                            message_data = {
                                'method': 'sendFile',
                                'body': inv.name,#,html2text.html2text(body) + inv.get_link(),
                                'phone': whatsapp,
                                'chatId': partner.chat_id or '',
                                #'body': attachment_ids.datas.split(",")[0],
                                'filename': attachment_ids.name,
                                'caption': html2text.html2text(body),#body.replace('_PARTNER_', partner.name).replace('_NUMBER_', inv.name).replace('_AMOUNT_TOTAL_', str(inv.format_amount(inv.amount_total, inv.currency_id)) if inv.currency_id else '').replace('\xa0', ' '),#att['caption'],
                            }
                            if partner.chat_id != whatsapp:
                                partner.chat_id = whatsapp
                                message_data.update({'chatId': whatsapp, 'phone': whatsapp, 'origin': inv.name, 'link': inv.get_link()})
                            # data_message = json.dumps(message_data)
                            # send_message = KlikApi.post_request(method='sendFile', data=data_message)
                            # if send_message.get('message')['sent']:
                            #     chatID = send_message.get('chatID')
                            #     status = 'send'
                            #     partner.chat_id = chatID
                            #     chatIDs.append(chatID)
                            #     _logger.warning('Success to send Message to WhatsApp number %s', whatsapp)
                            # else:
                            #     status = 'error'
                            #     _logger.warning('Failed to send Message to WhatsApp number %s', whatsapp)
                            # new_cr.commit()
                if message_data:             
                    AllchatIDs = ';'.join(chatIDs)
                    vals = WhatsappComposeMessage._prepare_mail_message(self.env.user.partner_id.id, AllchatIDs, inv and inv.id,  'account.move', body, message_data, subject, partners.ids, attachment_ids, send_message, status)
                    #vals = WhatsappComposeMessage._prepare_mail_message(self.env.user.partner_id.id, AllchatIDs, [inv.id], 'account.invoice', body, message_data, subject, partners.ids, attachment_ids, send_message, status)
                    MailMessage.sudo().create(vals)
                    new_cr.commit()
                    #time.sleep(3)
                            
