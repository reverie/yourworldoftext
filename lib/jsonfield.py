#http://www.djangosnippets.org/snippets/1478/

from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import simplejson as json

class DictField(models.TextField):
    """DictField is a textfield that contains JSON-serialized dictionaries."""

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""
        if isinstance(value, dict):
            return value
        value = json.loads(value)
        assert isinstance(value, dict)
        return value

    def get_db_prep_save(self, value):
        """Convert our JSON object to a string before we save"""
        assert isinstance(value, dict)
        value = json.dumps(value, cls=DjangoJSONEncoder)
        return super(DictField, self).get_db_prep_save(value)

