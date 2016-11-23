#! /usr/bin/env python
'''
The model module contains the Nerve class, the central component of the entire
nerve framework.

Platforrm:
    Unix

Author:
    Alex Braun <alexander.g.braun@gmail.com> <http://www.alexgbraun.com>
'''
# ------------------------------------------------------------------------------

from collections import defaultdict, namedtuple
import os
from pprint import pformat
import yaml
from schematics.exceptions import ValidationError
from nerve.core.utils import conform_keys, deep_update
from nerve.core.metadata import Metadata
from nerve.core.errors import KeywordError
from nerve.core.logger import Logger
# ------------------------------------------------------------------------------

class ProjectManager(object):
    '''
    Class for handling nerve projects

    Attributes:
        config (dict): a dictionary representing Nerve's internal configuration
        project_template (dict): a dictionary representing Nerve's internal project template

    API:
        create, clone, request, publish, delete, status and __getitem__

    Args:
        config (str or dict): a fullpath to a nerverc config or a dict of one

    Returns:
        Nerve
    '''
    def __init__(self, config):
        config = Metadata(config, spec='conf001', skip_keys=['environment'])
        config.validate()
        config = config.data
        self._config = config

        self._logger = Logger(level=config['log-level'])

        template = None
        if 'project-template' in config.keys():

            template = config['project-template']
            if os.path.exists(template):
                spec = None
                with open(template, 'r') as f:
                    spec = yaml.load(f)['specification']

                template = Metadata(template, config['project-root'], spec=spec)
                template.validate()
                template = template.data
                template['specification'] = spec
        self._project_template = template
    # --------------------------------------------------------------------------

    def __repr__(self):
        msg = 'CONFIG:\n'
        msg += pformat(self.config)
        msg += '\nPROJECT TEMPLATE:\n'
        msg += pformat(self.project_template)
        return msg

    def _log(self, result):
        log = getattr(self._logger, result['level'])
        return log(result['message'])

    def __get_config(self, config):
        r'''
        Convenience method for creating a new temporary configuration dict by
        overwriting a copy of the internal config with keyword arguments
        specified in config

        Args:
            config (dict): dict of keyword arguments (\**config)

        Returns:
            dict: new config
        '''
        output = self.config
        if config != {}:
            config = conform_keys(config)
            output = deep_update(output, config)
            output = Metadata(output, spec='conf001', skip_keys=['environment'])
            try:
                output.validate()
            except ValidationError as e:
                raise KeywordError(e)
            output = output.data
        return output

    def __get_project(self, name, notes, config, project):
        r'''
        Convenience method for creating a new temporary project dict by
        overwriting a copy of the internal project template, if it exists,
        with keyword arguments specified in project

        Args:
            name (str): name of project
            notes (str, None): notes to be added to metadata
            config (dict, None): \**config dictionary
            project (dict, None): \**config dictionary

        Returns:
            dict: project metadata
        '''
        project['project-name'] = name
        if notes != None:
            project['notes'] = notes

        if self._project_template != None:
            project = deep_update(self._project_template, project)

        return project

    def _get_info(self, name, notes='', config={}, project={}):
        r'''
        Convenience method for creating new temporary config

        Args:
            name (str): name of project
            notes (str, optional): notes to be added to metadata. Default: ''
            config (dict, optional): \**config dictionary. Default: {}
            project (dict, optional): project metadata. Default: {}

        Returns:
            namedtuple: tuple with conveniently named attributes
        '''
        if not isinstance(name, str):
            raise TypeError('name argument must be a string')
        # ----------------------------------------------------------------------

        config = self.__get_config(config)

        project = self.__get_project(name, notes, config, project)
        if 'private' in project.keys():
            private = project['private']
        else:
            project['private'] = config['private']

        remote = dict(
            username=config['username'],
            token=config['token'],
            organization=config['organization'],
            project_name=name,
            private=project['private'],
            url_type=config['url-type'],
            specification='remote'
        )
        # ----------------------------------------------------------------------

        # create info object
        Info = namedtuple('Info', ['config', 'project', 'remote', 'root'])
        info = Info(config, project, remote, config['project-root'])
        return info

    @property
    def config(self):
        '''
        dict: copy of this object's configuration
        '''
        return self._config

    @property
    def project_template(self):
        '''
        dict: copy of this object's project template
        '''
        return self._project_template
    # --------------------------------------------------------------------------

    def status(self, name, **config):
        r'''
        Reports on the status of all affected files within a given project

        Args:
            name (str): name of project. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            status_include_patterns (list, \**config): list of regular expressions user to include specific assets
            status_exclude_patterns (list, \**config): list of regular expressions user to exclude specific assets
            status_states (list, \**config): list of object states files are allowed to be in.
                Options: added, copied, deleted, modified, renamed, updated and untracked
            log-level (int, \**config): level of log-level for output. Default: 0
                Options: 0, 1, 2

        Yields:
            Metadata: Metadata object of each asset
        '''
        info = self._get_info(name, notes, config)
        project = Project(info.project, info.remote, info.root)
        result = project.status(**info.config)

        self._log(result)
        return result

    def create(self, name, notes=None, config={}, **project):
        r'''
        Creates a nerve project on Github and in the project-root folder

        Created items include:
            Github repository
            dev branch
            nerve project structure
            .lfsconfig
            .gitattributes
            .gitignore
            .git-credentials

        Args:
            name (str): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            config (dict, optional): config parameters, overwrites fields in a copy of self.config
            \**project: optional project parameters, overwrites fields in a copy of self.project_template

        Returns:
            bool: success status

        .. todo::
            - fix whetever causes the notebook kernel to die
            - send data to DynamoDB
        '''
        info = self._get_info(name, notes, config, project)
        project = Project(info.project, info.remote, info.root)
        project.create(**info.config)

        return self._log(result)

    def clone(self, name, **config):
        r'''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            name (str): name of project. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            log-level (int, \**config): level of log-level for output. Default: 0
                Options: 0, 1, 2
            user_branch (str, \**config): branch to clone from. Default: user's branch

        Returns:
            bool: success status

        .. todo::
            - catch repo already exists errors and repo doesn't exist errors
        '''
        info = self._get_info(name, config=config)
        project = Project(info.project, info.remote, info.root)
        project.clone(**info.config)

        return self._log(result)

    def request(self, name, **config):
        r'''
        Request deliverables from the dev branch of given project

        Args:
            name (str): name of project. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            user_branch (str, \**config): branch to pull deliverables into. Default: user's branch
            request_include_patterns (list, \**config): list of regular expressions user to include specific deliverables
            request_exclude_patterns (list, \**config): list of regular expressions user to exclude specific deliverables
            log-level (int, \**config): level of log-level for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status
        '''
        info = self._get_info(name, config=config)
        project = Project(info.project, info.remote, info.root)
        result = project.request(**info.config)

        return self._log(result)

    def publish(self, name, notes=None, **config):
        r'''
        Attempt to publish deliverables from user's branch to given project's dev branch on Github

        All assets will be published to the user's branch.
        If all deliverables are valid then all data and metadata will be commited
        to the user's branch and merged into the dev branch.
        If not only invalid metadata will be commited to the user's branch

        Args:
            name (str): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            user_branch (str, \**config): branch to pull deliverables from. Default: user's branch
            publish_include_patterns (list, \**config): list of regular expressions user to include specific assets
            publish_exclude_patterns (list, \**config): list of regular expressions user to exclude specific assets
            log-level (int, \**config): level of log-level for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status

        .. todo::
            - add branch checking logic to skip the following if not needed?
        '''
        info = self._get_info(name, notes, config)
        project = Project(info.project, info.remote, info.root)
        result = project.request(**info.config)

        return self._log(result)
    # --------------------------------------------------------------------------

    def delete(self, name, from_server, from_local, **config):
        r'''
        Deletes a nerve project

        Args:
            name (str): name of project. Default: None
            from_server (bool): delete Github project
            from_local (bool): delete local project directory
            \**config: optional config parameters, overwrites fields in a copy of self.config
            log-level (int, \**config): level of log-level for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status

        .. todo::
            - add git lfs logic for deletion
        '''
        info = self._get_info(name, config=config)
        project = Project(info.project, info.remote, info.root)
        result = project.delete(from_server, from_local)

        return self._log(result)
# ------------------------------------------------------------------------------

def main():
    '''
    Run help if called directly
    '''

    import __main__
    help(__main__)
# ------------------------------------------------------------------------------

__all__ = ['Nerve']

if __name__ == '__main__':
    main()
