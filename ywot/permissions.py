def can_read(user, world):
    from yourworld.ywot.models import Whitelist
    if world.public_readable:
        return True
    if not user.is_authenticated():
        return False
    if world.owner_id == user.id:
        return True
    if user.is_superuser:
        return True
    try:
        Whitelist.objects.get(user=user, world=world)
        return True
    except Whitelist.DoesNotExist:
        return False
       
def can_write(user, world):
    from yourworld.ywot.models import Whitelist
    if world.public_writable:
        return True
    if not user.is_authenticated():
        return False
    if world.owner_id == user.id:
        return True
    # Not allowing superuser to write. Be clean.
    try:
        Whitelist.objects.get(user=user, world=world)
        return True
    except Whitelist.DoesNotExist:
        return False

def can_admin(user, world):
    return bool(world.owner_id and (world.owner_id == user.id))

def can_coordlink(user, world):
    if not can_write(user, world):
        return False
    if can_admin(user, world):
        return True
    if world.properties.get('features', {}).get('coordLink', False):
        return True
    return False

def is_superuser(user):
    return user.is_authenticated() and user.is_superuser

def can_urllink(user, world):
    if not can_write(user, world):
        return False
    if can_admin(user, world):
        return True
    if world.properties.get('features', {}).get('coordLink', False):
        return True
    return False

def get_available_features(user, world):
    features = world.properties.get('features', {})
    if can_admin(user, world):
        coordLink = True
        go_to_coord = True
        urlLink = True
    else:
        coordLink = features.get('coordLink', False) and can_write(user, world)
        urlLink = features.get('urlLink', False) and can_write(user, world)
        go_to_coord = features.get('go_to_coord', False) or is_superuser(user)
    return {
            'coordLink': coordLink,
            'urlLink': urlLink,
            'go_to_coord': go_to_coord
            }

