"""
Odoo Subscriptions Manager v18.2+
Gestione abbonamenti e ordini ricorrenti semplificata
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from .odoo_client import OdooClient
from .odoo_exceptions import OdooDataError

try:
    from logger_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

class OdooSubscriptionManager:
    """Manager per la gestione degli abbonamenti Odoo"""
    
    def __init__(self, client: OdooClient):
        self.client = client
        self.logger = get_logger(__name__)
    
    def get_available_fields(self) -> List[str]:
        """Recupera i campi disponibili per sale.order"""
        try:
            fields_info = self.client.get_model_fields('sale.order')
            return list(fields_info.keys())
        except:
            return []
    
    def find_recurring_fields(self, available_fields: List[str]) -> List[str]:
        """Identifica i campi che indicano ricorrenza"""
        possible_fields = [
            'is_subscription', 'subscription', 'recurring', 'ricorrente',
            'subscription_management', 'subscription_id', 'recurrence_id',
            'is_recurring', 'subscription_template_id', 'subscription_state'
        ]
        
        return [field for field in possible_fields if field in available_fields]
    
    def get_orders_with_filters(self, partner_id: Optional[int] = None, limit: int = 100) -> tuple[List[Dict], List[str]]:
        """Recupera ordini con filtri di ricorrenza"""
        available_fields = self.get_available_fields()
        recurring_fields = self.find_recurring_fields(available_fields)
        
        # Costruisce filtri
        domain = [('state', 'in', ['sale', 'done'])]
        
        # Aggiunge filtri per ricorrenza
        if 'is_subscription' in available_fields:
            domain.append(('is_subscription', '=', True))
        elif 'subscription' in available_fields:
            domain.append(('subscription', '!=', False))
        
        # Filtro per partner specifico
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        
        # Campi da recuperare
        fields_to_get = [
            'id', 'name', 'partner_id', 'state', 'amount_total',
            'date_order', 'invoice_status', 'order_line', 'currency_id'
        ] + recurring_fields
        
        # Recupera ordini
        orders = self.client.execute(
            'sale.order', 'search_read',
            domain,
            fields=fields_to_get,
            order='date_order desc',
            limit=limit
        )
        
        return orders, recurring_fields
    
    def identify_subscriptions_manually(self, orders: List[Dict]) -> List[Dict]:
        """Identifica abbonamenti manualmente se non trovati con filtri diretti"""
        subscriptions = []
        
        for order in orders:
            is_subscription = False
            
            # Criterio 1: Cliente con più ordini
            partner_id = order['partner_id'][0] if order['partner_id'] else None
            if partner_id:
                similar_orders = self.client.execute(
                    'sale.order', 'search_count',
                    [
                        ('partner_id', '=', partner_id),
                        ('state', 'in', ['sale', 'done']),
                        ('id', '!=', order['id'])
                    ]
                )
                
                if similar_orders >= 2:
                    is_subscription = True
            
            # Criterio 2: Analisi prodotti per termini di abbonamento
            if order.get('order_line') and not is_subscription:
                try:
                    lines = self.client.execute(
                        'sale.order.line', 'search_read',
                        [('order_id', '=', order['id'])],
                        fields=['name', 'product_id']
                    )
                    
                    subscription_terms = [
                        'abbonamento', 'subscription', 'piano', 'canone',
                        'mensile', 'annuale', 'ricorrente', 'voip'
                    ]
                    
                    for line in lines:
                        line_name = (line.get('name', '') or '').lower()
                        product_name = ''
                        if line.get('product_id') and isinstance(line['product_id'], list):
                            product_name = (line['product_id'][1] or '').lower()
                        
                        if any(term in line_name or term in product_name for term in subscription_terms):
                            is_subscription = True
                            break
                            
                except Exception:
                    pass
            
            # Criterio 3: Righe con traffico extra
            if order.get('order_line') and not is_subscription:
                try:
                    extra_lines = self.client.execute(
                        'sale.order.line', 'search_count',
                        [
                            ('order_id', '=', order['id']),
                            ('name', 'like', 'EXTRA_TRAFFIC_')
                        ]
                    )
                    
                    if extra_lines > 0:
                        is_subscription = True
                        
                except:
                    pass
            
            if is_subscription:
                subscriptions.append(order)
        
        return subscriptions
    
    def analyze_order_lines(self, order_id: int) -> Optional[Dict]:
        """Analizza le righe di un ordine"""
        try:
            lines = self.client.execute(
                'sale.order.line', 'search_read',
                [('order_id', '=', order_id)],
                fields=['name', 'price_unit', 'product_uom_qty', 'price_subtotal', 'product_id']
            )
            
            extra_lines = []
            regular_lines = []
            
            for line in lines:
                # Aggiunge informazioni prodotto
                product_info = None
                if line.get('product_id'):
                    if isinstance(line['product_id'], list) and len(line['product_id']) > 1:
                        product_info = {
                            'id': line['product_id'][0],
                            'name': line['product_id'][1]
                        }
                    elif isinstance(line['product_id'], int):
                        product_info = {
                            'id': line['product_id'],
                            'name': 'N/A'
                        }
                
                line['product_info'] = product_info
                
                if 'EXTRA_TRAFFIC_' in line['name']:
                    extra_lines.append(line)
                else:
                    regular_lines.append(line)
            
            return {
                'total_lines': len(lines),
                'extra_lines': len(extra_lines),
                'regular_lines': len(regular_lines),
                'extra_amount': sum(line['price_subtotal'] for line in extra_lines),
                'regular_amount': sum(line['price_subtotal'] for line in regular_lines),
                'extra_details': extra_lines,
                'regular_details': regular_lines,
                'all_lines': lines
            }
            
        except Exception:
            return None
    
    def format_date(self, date_string: Optional[str]) -> Optional[Dict]:
        """Formatta date per JSON"""
        if date_string:
            try:
                date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return {
                    "iso": date_obj.isoformat(),
                    "formatted": date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    "date_only": date_obj.strftime('%Y-%m-%d')
                }
            except:
                return {"raw": date_string}
        return None
    
    def get_subscriptions_json(self, partner_id: Optional[int] = None, limit: int = 100) -> Optional[Dict]:
        """Recupera abbonamenti e restituisce JSON"""
        try:
            # Prova prima con filtri diretti
            orders, recurring_fields = self.get_orders_with_filters(partner_id, limit)
            
            # Se non trova niente, prova ricerca manuale
            if not orders:
                alternative_domain = [('state', 'in', ['sale', 'done'])]
                if partner_id:
                    alternative_domain.append(('partner_id', '=', partner_id))
                
                all_orders = self.client.execute(
                    'sale.order', 'search_read',
                    alternative_domain,
                    fields=[
                        'id', 'name', 'partner_id', 'state', 'amount_total',
                        'date_order', 'invoice_status', 'order_line', 'currency_id'
                    ],
                    order='date_order desc',
                    limit=limit * 2
                )
                
                orders = self.identify_subscriptions_manually(all_orders)
            
            if not orders:
                return {
                    "export_info": {
                        "export_date": datetime.now().isoformat(),
                        "total_subscriptions": 0,
                        "partner_filter": partner_id,
                        "status": "no_subscriptions_found"
                    },
                    "summary": {
                        "total_subscriptions": 0,
                        "total_amount": 0
                    },
                    "subscriptions": []
                }
            
            # Costruisce JSON
            json_data = {
                "export_info": {
                    "export_date": datetime.now().isoformat(),
                    "total_subscriptions": len(orders),
                    "partner_filter": partner_id,
                    "odoo_connection": {
                        "url": self.client.config.url,
                        "database": self.client.config.database
                    }
                },
                "summary": {
                    "total_subscriptions": len(orders),
                    "total_amount": 0,
                    "total_extra_traffic": 0,
                    "subscriptions_with_extra": 0,
                    "currency_breakdown": {},
                    "partner_breakdown": {}
                },
                "subscriptions": []
            }
            
            total_amount = 0
            total_extra = 0
            subscriptions_with_extra = 0
            
            # Processa ogni abbonamento
            for order in orders:
                partner_info = {
                    "id": order['partner_id'][0] if order['partner_id'] else None,
                    "name": order['partner_id'][1] if order['partner_id'] else None
                }
                
                currency_info = {
                    "id": order['currency_id'][0] if order.get('currency_id') else None,
                    "name": order['currency_id'][1] if order.get('currency_id') else 'EUR'
                }
                
                # Analizza righe
                lines_analysis = self.analyze_order_lines(order['id']) if order.get('order_line') else None
                
                # Aggiorna statistiche
                amount = order.get('amount_total', 0)
                total_amount += amount
                
                if lines_analysis and lines_analysis['extra_lines'] > 0:
                    total_extra += lines_analysis['extra_amount']
                    subscriptions_with_extra += 1
                
                # Breakdown per valuta
                currency_name = currency_info['name']
                if currency_name not in json_data['summary']['currency_breakdown']:
                    json_data['summary']['currency_breakdown'][currency_name] = {
                        "count": 0,
                        "total_amount": 0
                    }
                json_data['summary']['currency_breakdown'][currency_name]['count'] += 1
                json_data['summary']['currency_breakdown'][currency_name]['total_amount'] += amount
                
                # Breakdown per partner
                partner_name = partner_info['name'] or 'Unknown'
                if partner_name not in json_data['summary']['partner_breakdown']:
                    json_data['summary']['partner_breakdown'][partner_name] = {
                        "partner_id": partner_info['id'],
                        "subscriptions_count": 0,
                        "total_amount": 0
                    }
                json_data['summary']['partner_breakdown'][partner_name]['subscriptions_count'] += 1
                json_data['summary']['partner_breakdown'][partner_name]['total_amount'] += amount
                
                # Campi ricorrenza
                recurring_info = {}
                for field_name in recurring_fields:
                    if field_name in order and order[field_name]:
                        recurring_info[field_name] = order[field_name]
                
                # Struttura abbonamento
                subscription = {
                    "id": order['id'],
                    "name": order['name'],
                    "partner": partner_info,
                    "state": order['state'],
                    "amount_total": amount,
                    "currency": currency_info,
                    "dates": {
                        "order_date": self.format_date(order.get('date_order'))
                    },
                    "invoice_status": order.get('invoice_status'),
                    "recurring_fields": recurring_info,
                    "has_extra_traffic": False,
                    "extra_traffic_amount": 0,
                    "lines_summary": {
                        "total_lines": 0,
                        "regular_lines": 0,
                        "extra_lines": 0,
                        "regular_amount": 0,
                        "extra_amount": 0
                    }
                }
                
                # Aggiunge analisi righe
                if lines_analysis:
                    subscription.update({
                        "has_extra_traffic": lines_analysis['extra_lines'] > 0,
                        "extra_traffic_amount": lines_analysis['extra_amount'],
                        "lines_summary": {
                            "total_lines": lines_analysis['total_lines'],
                            "regular_lines": lines_analysis['regular_lines'],
                            "extra_lines": lines_analysis['extra_lines'],
                            "regular_amount": lines_analysis['regular_amount'],
                            "extra_amount": lines_analysis['extra_amount']
                        }
                    })
                    
                    # Dettagli traffico extra
                    if lines_analysis['extra_details']:
                        subscription['extra_traffic_details'] = []
                        for line in lines_analysis['extra_details']:
                            line_detail = {
                                "name": line['name'],
                                "amount": line['price_subtotal'],
                                "quantity": line.get('product_uom_qty', 1),
                                "unit_price": line.get('price_unit', 0),
                                "product": line.get('product_info')
                            }
                            
                            # Estrae periodo se possibile
                            if 'EXTRA_TRAFFIC_' in line['name']:
                                try:
                                    parts = line['name'].split('EXTRA_TRAFFIC_')[1].split('_')
                                    if len(parts) >= 2:
                                        line_detail['traffic_period'] = {
                                            "year": int(parts[0]),
                                            "month": int(parts[1]),
                                            "period_string": f"{parts[1]}/{parts[0]}"
                                        }
                                except:
                                    pass
                            
                            subscription['extra_traffic_details'].append(line_detail)
                    
                    # Dettagli righe regolari (prodotti abbonamento)
                    if lines_analysis['regular_details']:
                        subscription['subscription_products'] = []
                        for line in lines_analysis['regular_details']:
                            product_detail = {
                                "name": line['name'],
                                "amount": line['price_subtotal'],
                                "quantity": line.get('product_uom_qty', 1),
                                "unit_price": line.get('price_unit', 0),
                                "product": line.get('product_info')
                            }
                            subscription['subscription_products'].append(product_detail)
                    
                    # Riepilogo tutti i prodotti
                    subscription['all_products'] = []
                    for line in lines_analysis['all_lines']:
                        product_summary = {
                            "name": line['name'],
                            "amount": line['price_subtotal'],
                            "quantity": line.get('product_uom_qty', 1),
                            "unit_price": line.get('price_unit', 0),
                            "product": line.get('product_info'),
                            "type": "extra_traffic" if 'EXTRA_TRAFFIC_' in line['name'] else "subscription"
                        }
                        subscription['all_products'].append(product_summary)
                
                json_data['subscriptions'].append(subscription)
            
            # Aggiorna summary
            json_data['summary'].update({
                'total_amount': total_amount,
                'total_extra_traffic': total_extra,
                'subscriptions_with_extra': subscriptions_with_extra,
                'extra_traffic_percentage': (total_extra / total_amount * 100) if total_amount > 0 else 0
            })
            
            return json_data
            
        except Exception as e:
            self.logger.error(f"Errore recupero abbonamenti: {e}")
            return None