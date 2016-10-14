#! /usr/bin/env python
'''
The specifications module house all the specifications for nerve entities

Those entities include: configs, projects, assets (non-deliverables) and
deliverables.

All specifications used in production should be subclassed from the
aforementioned classes.  All class attributes must have a "get_[attribute]"
function in the traits module and should have one or more validators related t
the value of that trait (especially if required).
'''
# ------------------------------------------------------------------------------

import re
import nerve
from nerve.spec.traits import *
from nerve.spec.validators import *
from schematics.models import Model, BaseType
from schematics.types import StringType, IntType, BooleanType
from schematics.types.compound import ListType, DictType, ModelType
from schematics.exceptions import ValidationError
# ------------------------------------------------------------------------------

class MetaName(Model):
    '''
    Used for validating a metadata file's name

    A convenience class used by is_metapath in the validators module
    '''
    project_name  = StringType(required=True, validators=[is_project_name])
    specification = StringType(required=True, validators=[is_specification])
    descriptor    = StringType(required=True, validators=[])
    version       = IntType(required=True, validators=[is_version])
    render_pass   = StringType(validators=[is_render_pass])
    coordinate    = DictType(BaseType, validators=[is_coordinate])
    frame         = ListType(BaseType, validators=[is_frame])
    meta          = BooleanType(required=True, validators=[is_meta])
    extension     = StringType(required=True, default='yml', validators=[is_metadata_extension])
# ------------------------------------------------------------------------------

class Specification(Model):
    '''
    Base class from which all nerve specifications are subclassed

    Attributes:
        specification (str): same as class name
    '''
    def __init__(self, raw_data={}):
        '''
        Sets specification to class name

        Args:
            arg (dict): data to be run though a specification
        '''
        data = raw_data
        if 'specification' not in data.keys():
            data['specification'] = self.__class__.__name__.lower()
        # needed because python doesn't support hyphenated attributes
        data = {re.sub('-', '_', k): v for k,v in data.items()}
        if 'project' in data.keys():
            if data['project'] != {}:
                data['project'] = {re.sub('-', '_', k): v for k,v in data['project'].items()}
        super().__init__(raw_data=data)

    specification = StringType(required=True)

class Project(Specification):
    '''
    Base class for all nerve projects
    '''
    project_name   = StringType(required=True, validators=[is_project_name])
    project_id     = StringType(required=True, validators=[is_project_id])
    url            = StringType(required=True, validators=[is_url])
    notes          = StringType(default='')

    version        = IntType(required=True, validators=[is_version])
    teams          = DictType(StringType, required=True, validators=[is_teams])
    gitignore      = ListType(StringType, required=True, validators=[])
    private        = BooleanType(required=True, validators=[is_private])
    lfs_extensions = ListType(StringType, required=True, validators=[is_extension])
    assets         = ListType(StringType, default=[], validators=[])
    deliverables   = ListType(StringType, required=True, validators=[is_specification])

class NonDeliverable(Specification):
    '''
    Base class for all nerve non-deliverable assets
    '''
    project_name = StringType(required=True, validators=[is_project_name])
    project_id   = StringType(required=True, validators=[is_project_id])
    url          = StringType(required=True, validators=[is_url])
    notes        = StringType(default='')
    deliverable  = BooleanType(default=False)

class Deliverable(Specification):
    '''
    Base class for all nerve deliverable assets
    '''
    project_name = StringType(required=True, validators=[is_project_name])
    project_id   = StringType(required=True, validators=[is_project_id])
    url          = StringType(required=True, validators=[is_url])
    notes        = StringType(default='')

    version      = IntType(required=True, validators=[is_version])
    asset_name   = StringType(required=True, validators=[])
    asset_id     = StringType(required=True, validators=[is_asset_id])
    data         = ListType(StringType, validators=[is_file, is_path, is_exists])
    descriptor   = StringType(required=True, validators=[is_descriptor])
    dependencies = ListType(StringType, default=[])
    deliverable  = BooleanType(default=True)

class Config(Specification):
    '''
    Base class for all nerve configs (nerverc)
    '''
    username                 = StringType(required=True, validators=[is_username])
    user_branch              = StringType(required=True, validators=[is_user_branch])
    organization             = StringType(required=True, validators=[is_organization])
    project_root             = StringType(required=True, validators=[is_project_root])
    token                    = StringType(required=True, validators=[is_token])
    url_type                 = StringType(required=True, validators=[is_url_type])
    specification            = StringType(required=True, validators=[is_specification])
    request_include_patterns = ListType(StringType, default=[], validators=[is_request_include_patterns])
    request_exclude_patterns = ListType(StringType, default=[], validators=[is_request_exclude_patterns])
    publish_include_patterns = ListType(StringType, default=[], validators=[is_publish_include_patterns])
    publish_exclude_patterns = ListType(StringType, default=[], validators=[is_publish_exclude_patterns])
    status_states            = ListType(StringType, default=[], validators=[is_status_state])
    status_asset_types       = ListType(StringType, default=[], validators=[is_status_asset_type])
    verbosity                = IntType(default=0)
    project                  = ModelType(Project)

    def validate_project(self, key, data):
        is_specification(data['specification'])
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = [
    'Config',
    'Project',
    'Deliverable',
    'NonDeliverable'
]

if __name__ == '__main__':
    main()
