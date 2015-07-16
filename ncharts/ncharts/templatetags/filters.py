from django import template

register = template.Library()

@register.filter
def get_long_name(vs, v):
    """Get 'long_name' value of vs[v] """
    try:
        return vs[v]['long_name']
    except:
        return ''


