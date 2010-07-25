import os, re

def here(*args): 
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *args)

def req_render_to_response(request, template, context=None):
    from django.shortcuts import render_to_response
    from django.template import RequestContext
    context = context or {}
    rc = RequestContext(request, context)
    return render_to_response(template, context_instance=rc)

# This block is from http://stackoverflow.com/questions/92438/
control_chars = ''.join(map(unichr, range(0,32) + range(127,160)))
control_chars_set = set(control_chars)
control_char_re = re.compile('[%s]' % re.escape(control_chars))
def remove_control_chars(s):
    return control_char_re.sub('', s)

