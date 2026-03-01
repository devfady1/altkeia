from django import template
import json

register = template.Library()

@register.filter
def order_items_json(order):
    """
    Returns a JSON string of order items for the edit modal:
    [{'id': item.id, 'name': item.display_name, 'qty': item.quantity, 'notes': item.notes}]
    """
    if not order:
        return "[]"
    
    items_data = []
    for item in order.items.all():
        items_data.append({
            'id': item.id,
            'name': item.display_name,
            'qty': item.quantity,
            'notes': item.notes or '',
        })
    return json.dumps(items_data)

@register.filter
def session_items_json(session):
    """
    Returns a JSON string of all order items in a session for the edit modal:
    [{'id': item.id, 'name': item.display_name, 'qty': item.quantity, 'notes': item.notes}]
    """
    if not session:
        return "[]"
    
    items_data = []
    for order in session.orders.exclude(status='cancelled'):
        for item in order.items.all():
            items_data.append({
                'id': item.id,
                'name': item.display_name,
                'qty': item.quantity,
                'notes': item.notes or '',
            })
    return json.dumps(items_data)
