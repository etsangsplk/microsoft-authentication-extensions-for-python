"""Implements a Linux specific TokenCache, and provides auxiliary helper types.

This module depends on PyGObject. But `pip install pygobject` would typically fail,
until you install its dependencies first. For example, on a Debian Linux, you need::

    sudo apt install libgirepository1.0-dev libcairo2-dev python3-dev gir1.2-secret-1
    pip install pygobject

Alternatively, you could skip Cairo & PyCairo, but you still need to do all these
(derived from https://gitlab.gnome.org/GNOME/pygobject/-/issues/395)::

    sudo apt install libgirepository1.0-dev python3-dev gir1.2-secret-1
    pip install wheel
    PYGOBJECT_WITHOUT_PYCAIRO=1 pip install --no-build-isolation pygobject
"""
import logging

import gi  # https://pygobject.readthedocs.io/en/latest/getting_started.html

# pylint: disable=no-name-in-module
gi.require_version("Secret", "1")  # Would require a package gir1.2-secret-1
# pylint: disable=wrong-import-position
from gi.repository import Secret  # Would require a package gir1.2-secret-1


logger = logging.getLogger(__name__)

class LibSecretAgent(object):
    """A loader/saver built on top of low-level libsecret"""
    # Inspired by https://developer.gnome.org/libsecret/unstable/py-examples.html
    def __init__(  # pylint: disable=too-many-arguments
            self,
            schema_name,
            attributes,  # {"name": "value", ...}
            label="",  # Helpful when visualizing secrets by other viewers
            attribute_types=None,  # {name: SchemaAttributeType, ...}
            collection=None,  # None means default collection
            ):  # pylint: disable=bad-continuation
        """This agent is built on top of lower level libsecret API.

        Content stored via libsecret is associated with a bunch of attributes.

        :param string schema_name:
            Attributes would conceptually follow an existing schema.
            But this class will do it in the other way around,
            by automatically deriving a schema based on your attributes.
            However, you will still need to provide a schema_name.
            load() and save() will only operate on data with matching schema_name.

        :param dict attributes:
            Attributes are key-value pairs, represented as a Python dict here.
            They will be used to filter content during load() and save().
            Their arbitrary keys are strings.
            Their arbitrary values can MEAN strings, integers and booleans,
            but are always represented as strings, according to upstream sample:
            https://developer.gnome.org/libsecret/0.18/py-store-example.html

        :param string label:
            It will not be used during data lookup and filtering.
            It is only helpful when/if you visualize secrets by other viewers.

        :param dict attribute_types:
            Each key is the name of your each attribute.
            The corresponding value will be one of the following three:

            * Secret.SchemaAttributeType.STRING
            * Secret.SchemaAttributeType.INTEGER
            * Secret.SchemaAttributeType.BOOLEAN

            But if all your attributes are Secret.SchemaAttributeType.STRING,
            you do not need to provide this types definition at all.

        :param collection:
            The default value `None` means default collection.
        """
        self._collection = collection
        self._attributes = attributes or {}
        self._label = label
        self._schema = Secret.Schema.new(schema_name, Secret.SchemaFlags.NONE, {
            k: (attribute_types or {}).get(k, Secret.SchemaAttributeType.STRING)
            for k in self._attributes})

    def save(self, data):
        """Store data. Returns a boolean of whether operation was successful."""
        return Secret.password_store_sync(
            self._schema, self._attributes, self._collection, self._label,
            data, None)

    def load(self):
        """Load a password in the secret service, return None when found nothing"""
        return Secret.password_lookup_sync(self._schema, self._attributes, None)

    def clear(self):
        """Returns a boolean of whether any passwords were removed"""
        return Secret.password_clear_sync(self._schema, self._attributes, None)


def trial_run():
    """This trial run will raise an exception if libsecret is not functioning.

    Even after you installed all the dependencies so that your script can start,
    or even if your previous run was successful, your script could fail next time,
    for example when it will be running inside a headless SSH session.

    You do not have to do trial_run. The exception would also be raised by save().
    """
    try:
        agent = LibSecretAgent("Test Schema", {"attr1": "foo", "attr2": "bar"})
        payload = "Test Data"
        agent.save(payload)  # It would fail when running inside an SSH session
        assert agent.load() == payload  # This line is probably not reachable
        agent.clear()
    except (gi.repository.GLib.Error, AssertionError):
        message = (
            "libsecret did not perform properly. Please refer to "
            "https://github.com/AzureAD/microsoft-authentication-extensions-for-python/wiki/Encryption-on-Linux")  # pylint: disable=line-too-long
        logger.exception(message)  # This log contains trace stack for debugging
        logger.warning(message)  # This is visible by default
        raise

