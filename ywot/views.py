import collections, datetime, itertools, re, urlparse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, redirect
from django.utils import simplejson

from yourworld.helpers import req_render_to_response
from yourworld.lib import log
from yourworld.ywot.models import Tile, World, Edit, Whitelist
from yourworld.ywot import permissions

#
# Helpers
#

class ClaimException(Exception):
    pass

def do_claim(user, world):
    assert not world.owner
    world.owner = user
    world.save()

def claim(user, worldname):
    # TODO: write tests for this
    if not re.match('\w+$', worldname):
        raise ClaimException, "Invalid world name."
    world, new = World.get_or_create(worldname)
    if new:
        return do_claim(user, world)
    if world.owner:
        raise ClaimException, "That world already has an owner."
    editors = set(world.edit_set.all().values_list('user', flat=True))
    if not editors:
        return do_claim(user, world)
    if len(editors) > 2:
        raise ClaimException, "Too many people have edited that world."
    if len(editors) == 2:
        if editors == set([user, None]):
            return do_claim(user, world)
        else:
            raise ClaimException, "Too many people have edited that world."
    assert len(editors) == 1
    obj = editors.pop()
    if obj == user:
        return do_claim(user, world)
    if obj is not None:
        raise ClaimException, "Too many people have edited that world."
    if world.created_at > datetime.datetime.now() - datetime.timedelta(minutes=5):
        raise ClaimException, "That world has been around too long to claim."
    return do_claim(user, world)

def try_add_member(world, username):
    """Return success/error message."""
    try:
        u = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return 'User not found'
    if u == world.owner:
        return 'User is already the owner of "%s"' % world.name
    Whitelist.objects.get_or_create(world=world, user=u)
    return '%s is now a member of the "%s" world' % (username, world.name)
    

def date_range(from_date, to_date, step=datetime.timedelta(days=1)):
    # from http://www.ianlewis.org/en/python-date-range-iterator
    while from_date <= to_date:
        yield from_date
        from_date = from_date + step
    return
    
def get_counts(obj_iter, key_getter):
    """
    Assumes iterable is sorted by key. Returns a defaultdict
    of count of iterables with each key.
    """
    result = collections.defaultdict(int)
    for key, group in itertools.groupby(obj_iter, key_getter):
        result[key] = len(list(group))
    return result
        
def response_403():
    # TODO: returns JS content type here and elsewhere
    response = HttpResponse(simplejson.dumps('No permission'))
    response.status_code = 403
    return response

#
# World Views
#

def yourworld(request, namespace):
    """Check permissions and route request."""
    world, _ = World.get_or_create(namespace)
    if not permissions.can_read(request.user, world):
        return HttpResponseRedirect('/accounts/private/')
    if 'fetch' in request.GET:
        return fetch_updates(request, world)
    can_write = permissions.can_write(request.user, world)
    if request.method == 'POST':
        if not can_write:
            return response_403()
        return send_edits(request, world)
    state = {
        'canWrite': can_write,
        'canAdmin': permissions.can_admin(request.user, world),
        'worldName': world.name,
        'features': permissions.get_available_features(request.user, world),
    }
    if 'MSIE' in request.META.get('HTTP_USER_AGENT', ''):
        state['announce'] = "Sorry, your World of Text doesn't work well with Internet Explorer."
    return req_render_to_response(request, 'yourworld.html', {
        'settings': settings,
        'state': simplejson.dumps(state),
    })
    
def fetch_updates(request, world):
    response = {}
    min_tileY = int(request.GET['min_tileY'])
    min_tileX = int(request.GET['min_tileX'])
    max_tileY = int(request.GET['max_tileY'])
    max_tileX = int(request.GET['max_tileX'])
    response = {}

    assert min_tileY < max_tileY
    assert min_tileX < max_tileX
    assert ((max_tileY - min_tileY)*(max_tileX - min_tileX)) < 400
    
    # Set default info to null
    for tileY in xrange(min_tileY, max_tileY + 1): #+1 b/c of range bounds
        for tileX in xrange(min_tileX, max_tileX + 1):
            response["%d,%d" % (tileY, tileX)] = None
            
    tiles = Tile.objects.filter(world=world,
                                tileY__gte=min_tileY, tileY__lte=max_tileY,
                                tileX__gte=min_tileX, tileX__lte=max_tileX)
    for t in tiles:
        tile_key = "%s,%s" % (t.tileY, t.tileX)
        if (int(request.GET.get('v', 0)) == 2):
            d = {'content': t.content.replace('\n', ' ')}
            if 'protected' in t.properties: # We want to send *any* set value (case: reset to false)
                d['protected'] = t.properties['protected']
            response[tile_key] = d
        elif (int(request.GET.get('v', 0)) == 3):
            d = {'content': t.content.replace('\n', ' ')}
            if t.properties:
                d['properties'] = t.properties
            response[tile_key] = d
        else:
            raise ValueError, 'Unknown JS version'
    return HttpResponse(simplejson.dumps(response))
    
def send_edits(request, world):
    assert permissions.can_write(request.user, world) # Checked by router
    response = []
    tiles = {} # a simple cache
    edits = [e.split(',', 5) for e in request.POST.getlist('edits')]
    for edit in edits:
        char = edit[5]
        tileY, tileX, charY, charX, timestamp = map(int, edit[:5])
        assert len(char) == 1 # TODO: investigate these tracebacks
        keyname = "%d,%d" % (tileY, tileX)
        if keyname in tiles:
            tile = tiles[keyname]
        else:
            # TODO: select for update
            tile, _ = Tile.objects.get_or_create(world=world, tileY=tileY, tileX=tileX)
            tiles[keyname] = tile
        if tile.properties.get('protected'):
            if not permissions.can_admin(request.user, world):
                continue    
        tile.set_char(charY, charX, char)
        # TODO: anything, please.
        if tile.properties:
            if 'cell_props' in tile.properties:
                if str(charY) in tile.properties['cell_props']: #must be str because that's how JSON interprets int keys
                    if str(charX) in tile.properties['cell_props'][str(charY)]:
                        del tile.properties['cell_props'][str(charY)][str(charX)]
                        if not tile.properties['cell_props'][str(charY)]:
                            del tile.properties['cell_props'][str(charY)]
                            if not tile.properties['cell_props']:
                                del tile.properties['cell_props']
        response.append([tileY, tileX, charY, charX, timestamp, char])
    if len(edits) < 200:
        for tile in tiles.values():
            tile.save()
        Edit.objects.create(world=world, 
                            user=request.user if request.user.is_authenticated() else None,
                            content=repr(edits),
                            ip=request.META['REMOTE_ADDR'],
                            )
    return HttpResponse(simplejson.dumps(response))

#
# Account Views
#

def home(request):
    """The main front-page other than a world."""
    return req_render_to_response(request, 'home.html')

@login_required
def profile(request):
    worlds_owned = World.objects.filter(owner=request.user)
    memberships = World.objects.filter(whitelist__user=request.user)
    context = {'worlds_owned': worlds_owned, 'memberships': memberships}
    if request.method == 'POST':
        worldname = request.POST['worldname']
        try:
            claim(request.user, worldname)
            context['claimed'] = True
            context['message'] = 'World "%s" successfully claimed.' % worldname
        except ClaimException, msg:
            context['claimed'] = False
            context['message'] = msg
    return req_render_to_response(request, 'profile.html', context)

@login_required
def configure(request, worldname):
    try:
        world = World.objects.get(name__iexact=worldname, owner=request.user)
    except World.DoesNotExist:
        # TODO: log security?
        return redirect('profile')
    add_member_message = None
    if request.method == 'POST':
        if request.POST['form'] == 'public_perm':
            pp = request.POST['public_perm']
            if pp == 'none':
                world.public_readable = False
                world.public_writable = False
            elif pp == 'read':
                world.public_readable = True
                world.public_writable = False
            else:
                assert pp == 'write'
                world.public_readable = True
                world.public_writable = True
            world.save()
        elif request.POST['form'] == 'add_member':
            add_member_message = try_add_member(world, request.POST['add_member'])
        elif request.POST['form'] == 'remove_member':
            to_remove = [key for key in request.POST.keys() if key.startswith('remove_')]
            assert len(to_remove) == 1
            username_to_remove = to_remove[0].split('_')[1]
            wl = Whitelist.objects.get(world=world, user__username=username_to_remove)
            wl.delete()
        elif request.POST['form'] == 'features':
            # TODO: move this crap into JSONField so I can do world.properties.features.go_to_coordinates = ...
            features = world.properties.get('features', {})
            features['go_to_coord'] = bool(int(request.POST['go_to_coord']))
            features['coordLink'] = bool(int(request.POST['coordLink']))
            features['urlLink'] = bool(int(request.POST['urlLink']))
            world.properties['features'] = features
            world.save()
        else:
            raise ValueError, "Unknown form type"
            
    if world.public_writable:
        public_perm = 'write'
    elif world.public_readable:
        public_perm = 'read'
    else:
        public_perm = 'none'
    return req_render_to_response(request, 'configure.html', {
        'world': world,
        'public_perm': public_perm,
        'members': User.objects.filter(whitelist__world=world).order_by('username'),
        'add_member_message': add_member_message
        })
    
def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect(reverse('home'))

def private(request):
    return req_render_to_response(request, 'private.html')
    
def member_autocomplete(request):
    if not request.user.is_authenticated():
        return response_403()
    q = request.GET['q']
    assert q
    # TODO: filter by is_active? only if we aren't going to accept those as input...
    users = (User.objects
             .filter(username__istartswith=q)
             .order_by('username')
             .values_list('username', flat=True))[:10]
    return HttpResponse('\n'.join(users))

def protect(request):
    world = World.objects.get(name=request.POST['namespace'])
    if not permissions.can_admin(request.user, world):
        return response_403()
    tileY, tileX = request.POST['tileY'], request.POST['tileX']
    # TODO: select for update
    tile, _ = Tile.objects.get_or_create(world=world, tileY=tileY, tileX=tileX)
    tile.properties['protected'] = True
    tile.save()
    log.info('ACTION:PROTECT %s %s %s' % (world.id, tileY, tileX))
    return HttpResponse('')
    
def unprotect(request):
    # TODO: factor out w/above
    # TODO: make return javascript
    world = World.objects.get(name=request.POST['namespace'])
    if not permissions.can_admin(request.user, world):
        return response_403()
    tileY, tileX = request.POST['tileY'], request.POST['tileX']
    # TODO: select for update
    tile, _ = Tile.objects.get_or_create(world=world, tileY=tileY, tileX=tileX)
    tile.properties['protected'] = False
    tile.save()
    log.info('ACTION:UNPROTECT %s %s %s' % (world.id, tileY, tileX))
    return HttpResponse('')

def coordlink(request):
    world = World.objects.get(name=request.POST['namespace'])
    if not permissions.can_coordlink(request.user, world):
        return response_403()
    tileY, tileX = int(request.POST['tileY']), int(request.POST['tileX'])
    tile, _ = Tile.objects.get_or_create(world=world, tileY=tileY, tileX=tileX)
    if tile.properties.get('protected'):
        if not permissions.can_admin(request.user, world):
            # TODO: log?
            return HttpResponse('')
    # Must convert to str because that's how JsonField reads the existing keys
    charY = int(request.POST['charY'])
    charX = int(request.POST['charX'])
    assert charY < Tile.ROWS
    assert charX < Tile.COLS
    charY, charX = str(charY), str(charX)
    link_tileY = str(int(request.POST['link_tileY']))
    link_tileX = str(int(request.POST['link_tileX']))
    if 'cell_props' not in tile.properties:
        tile.properties['cell_props'] = {}
    if charY not in tile.properties['cell_props']:
        tile.properties['cell_props'][charY] = {}
    if charX not in tile.properties['cell_props'][charY]:
        tile.properties['cell_props'][charY][charX] = {}
    tile.properties['cell_props'][charY][charX]['link'] = {
            'type': 'coord',
            'link_tileY': link_tileY,
            'link_tileX': link_tileX,
            }
    tile.save()
    log.info('ACTION:COORDLINK %s %s %s %s %s %s %s' % (world.id, tileY, tileX, charY, charX, link_tileY, link_tileX))
    return HttpResponse('')

def urllink(request):
    # TODO: factor out w/above
    world = World.objects.get(name=request.POST['namespace'])
    if not permissions.can_urllink(request.user, world):
        return response_403()
    tileY, tileX = int(request.POST['tileY']), int(request.POST['tileX'])
    tile, _ = Tile.objects.get_or_create(world=world, tileY=tileY, tileX=tileX)
    if tile.properties.get('protected'):
        if not permissions.can_admin(request.user, world):
            # TODO: log?
            return HttpResponse('')
    # Must convert to str because that's how JsonField reads the existing keys
    charY = int(request.POST['charY'])
    charX = int(request.POST['charX'])
    assert charY < Tile.ROWS
    assert charX < Tile.COLS
    charY, charX = str(charY), str(charX)
    url = request.POST['url'].strip()
    if not urlparse.urlparse(url)[0]: # no scheme
        url = 'http://' + url
    if 'cell_props' not in tile.properties:
        tile.properties['cell_props'] = {}
    if charY not in tile.properties['cell_props']:
        tile.properties['cell_props'][charY] = {}
    if charX not in tile.properties['cell_props'][charY]:
        tile.properties['cell_props'][charY][charX] = {}
    tile.properties['cell_props'][charY][charX]['link'] = {
            'type': 'url',
            'url': url,
            }
    tile.save()
    log.info('ACTION:URLLINK %s %s %s %s %s %s' % (world.id, tileY, tileX, charY, charX, url))
    return HttpResponse('')
