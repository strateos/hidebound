#! /usr/bin/env python
import os
import re
import yaml
from itertools import *
from warnings import warn
from nerve.spec import specifications, traits
from nerve.core.errors import SpecificationError
# ------------------------------------------------------------------------------
'''
The metadata module contain the Metadata class which is used by nerve to handle all metadata
'''

class Metadata(object):
    '''
    The Metadata class provides a simple object for generating, validating and writing metadata

    Internally, Metadata generates a specification class found in the specifications module.
    Those specification classes are themselves subclassed from schematics.model.Model.

    API: data, get_traits, validate, write, __getitem__
    '''
    def __init__(self, item):
        '''
        Metadata constructor takes a dict, filepath or dirpath and turns it into internal metadata
        The specification class used to wrap the internal data is derived from item.

        Args:
            item (dict or str): a dict of asset metadata, an asset yml file or
                                the fullpath of an asset file or directory
        Returns:
            Metadata

        Raises:
            OSError, TypeError
        '''
        spec = None
        if isinstance(item, dict):
            spec = item['specification']

        elif isinstance(item, str):
            if not os.path.exists(item):
                raise OSError('No such file or directory: ' + item)

            root, name = os.path.split(item)
            root, spec = os.path.split(root)
            name, ext = os.path.splitext(name)


            if re.search('nerverc', name):
                spec = 'config001'
                ext = 'yml'

            if ext in ['yml', 'yaml']:
                self._metapath = item
                with open(item, 'r') as f:
                    item = yaml.load(f)

            else:
                self._datapath = item
                item = dict(
                    specification=spec
                )

        else:
            raise TypeError('type: ' + type(item) + ' not supported')

        spec = self._get_spec(spec)
        self.__data = spec(item)

    def __getitem__(self, key):
        return self.data[key]

    def _get_spec(self, name):
        '''
        Convenience method that returns a class from the specifications module of the same name

        Args:
            name (str): specification class name (all lowercase is fine)

        Returns:
            Specification: specification of class "name"
        '''
        name = name.capitalize()
        if hasattr(specifications, name):
            return getattr(specifications, name)
        else:
            raise SpecificationError('"' + name + '" specification not found in specifications module')
    # --------------------------------------------------------------------------

    def get_traits(self):
        '''
        Generates metadata from evaluating data files pointed to provided metadata
        Uses trait function from the traits module to overwrites internal data
        with new values

        Args:
            None

        Returns:
            dict: traits
        '''
        output = {}
        for key in self.__data.keys():
            trait = 'get_' + key
            if hasattr(traits, trait):
                trait = getattr(traits, trait)
                output[key] = trait(self._datapath)

        self.__data.import_data(output)
        return output

    @property
    def data(self):
        '''
        Internal data property

        Returns:
            dict: internal data
        '''
        output = self.__data.to_primitive()
        return {re.sub('_', '-', k): v for k,v in output.items()}

    def validate(self):
        '''
        Validates internal data accodring to specification

        Args:
            None

        Return:
            bool: validity
        '''
        return self.__data.validate() == None

    def write(self, fullpath=None):
        '''
        Writes internal data to file with correct name in correct location

        Args:
            fullpath (str, optional): full path to yml metadata file

        Returns:
            bool: success status
        '''
        if not fullpath:
            fullpath = self._metapath
        meta = nerve.spec.traits.get_name_traits(fullpath)
        specifications.MetaName(meta).validate()

        # overwrite existing metadata
        data = {}
        if os.path.exists(fullpath):
            with open(fullpath, 'r') as f:
                data = yaml.load(f)

        data.update(self.__data.to_primitive())

        with open(fullpath, 'w') as f:
            yaml.dump(data, f)

        return os.path.exists(fullpath)
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['Metadata']

if __name__ == '__main__':
    main()
