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
from itertools import chain
import os
from pprint import pformat
import re
import shutil
from warnings import warn
from schematics.exceptions import ValidationError
from nerve.core.utils import conform_keys, deep_update
from nerve.core.git import Git
from nerve.core.git_lfs import GitLFS
from nerve.core.client import Client
from nerve.core.metadata import Metadata
from nerve.core.errors import KeywordError
# ------------------------------------------------------------------------------

class Nerve(object):
    '''
    Class for handling nerve projects

    Attributes:
        config (dict): a dictionary representing Nerve's internal configuration

    API:
        create, clone, request, publish, delete, status and __getitem__

    Args:
        config (str or dict): a fullpath to a nerverc config or a dict of one

    Returns:
        Nerve
    '''
    def __init__(self, config):
        config = Metadata(config, spec='config', skip_keys=['environment'])
        config.validate()
        self.__config = config
    # --------------------------------------------------------------------------

    def __getitem__(self, key):
        return self.config[key]

    def __repr__(self):
        return pformat(self.config)

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
            output = Metadata(output, spec='config', skip_keys=['environment'])
            try:
                output.validate()
            except ValidationError as e:
                raise KeywordError(e)
            output = output.data
        return output

    def _get_info(self, name, notes, config):
        r'''
        Convenience method for creating new temporary config

        Args:
            name (str): name of project
            notes (str): notes to be added to metadata
            config (dict): \**config dictionary

        Returns:
            namedtuple: tuple with conveniently named attributes
        '''
        config = self.__get_config(config)
        project = config['project']

        if name == None:
            name = project['project-name']
        if notes == None:
            notes = project['notes']

        project['project-name'] = name
        project['notes'] = notes

        path = os.path.join(config['project-root'], name)

        client_conf = dict(
            username=config['username'],
            token=config['token'],
            organization=config['organization'],
            project_name=project['project-name'],
            private=project['private'],
            url_type=config['url-type'],
            specification='client'
        )
        # ----------------------------------------------------------------------

        info = namedtuple('Info', ['config', 'project', 'name', 'path',
           'states', 'asset_types', 'branch', 'verbosity', 'client_conf',
           'notes', 'env', 'lfs_url', 'git_creds']
        )
        info = info(
            config,
            project,
            name,
            path,
            config['status-states'],
            config['status-asset-types'],
            config['user-branch'],
            config['verbosity'],
            client_conf,
            notes,
            config['environment'],
            config['lfs-server-url'],
            config['git-credentials']
        )
        return info

    @property
    def config(self):
        '''
        dict: copy of this object's configuration
        '''
        return self.__config.data
    # --------------------------------------------------------------------------

    def status(self, name=None, **config):
        r'''
        Reports on the status of all affected files within a given project

        Args:
            name (str, optional): name of project. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            status_include_patterns (list, \**config): list of regular expressions user to include specific assets
            status_exclude_patterns (list, \**config): list of regular expressions user to exclude specific assets
            status_states (list, \**config): list of object states files are allowed to be in.
                Options: added, copied, deleted, modified, renamed, updated and untracked
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Yields:
            Metadata: Metadata object of each asset
        '''
        info = self._get_info(name, None, config)

        warn_ = False
        if info.verbosity == 2:
            warn_ = True

        local = Git(info.path, environment=info.env)
        local.reset()
        local.add(all=True) # git lfs cannot get the status of unstaged files
        lfs = GitLFS(info.path, environment=info.env)
        files = lfs.status(
            include=info.config['status-include-patterns'],
            exclude=info.config['status-exclude-patterns'],
            warnings=warn_
        )
        # ----------------------------------------------------------------------

        # aggregate the data into prototype pattern (unique keys with list values)
        agg = defaultdict(lambda: defaultdict(lambda: []))
        for file in files:
            asset = file['path'].split(os.sep)
            if len(asset) > 2:
                asset = os.path.join(asset[0], asset[1])
                asset = re.search('.*' + asset, file['fullpath'])
                asset = asset.group(0)
            else:
                asset = file['fullpath']

            for k, v in file.items():
                agg[asset][k].append(v)

        local.reset()
        # ----------------------------------------------------------------------

        for asset, v in sorted(agg.items()):
            if info.states:
                rogue_states = set(v['state']).difference(info.states)
                if len(rogue_states) > 0:
                    if info.verbosity > 0:
                        warn(asset + ' contains files of state: ' + ','.join(rogue_states))
                    continue

            output = Metadata(asset)
            if output.data['asset-type'] in info.asset_types:
                output.get_traits()
                yield output

    def create(self, name=None, notes=None, **config):
        r'''
        Creates a nerve project on Github and in the project-root folder

        Created items include:
            Github repository
            dev branch
            nerve project structure
            .lfsconfig
            .gitattributes
            .gitignore

        Args:
            name (str, optional): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            project (dict, \**config): project metadata.
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status

        .. todo::
            - fix whetever causes the notebook kernel to die
            - send data to DynamoDB
        '''
        # create repo
        info = self._get_info(name, notes, config)
        project = info.project

        client = Client(info.client_conf)
        local = Git(info.path, url=client['url'], environment=info.env)
        # ----------------------------------------------------------------------

        # configure repo
        lfs = GitLFS(info.path, environment=info.env)
        lfs.install(skip_smudge=True)
        lfs.create_config(info.lfs_url)
        lfs.track(['*.' + x for x in project['lfs-extensions']])

        local.create_gitignore(project['gitignore'])
        local.create_git_credentials(info.git_creds)
        # ----------------------------------------------------------------------

        # ensure first commit is on master branch
        local.add(all=True)
        local.commit('initial commit')
        local.push('master')
        # ----------------------------------------------------------------------

        # create project structure
        local.branch('dev')
        for subdir in chain(project['deliverables'], project['nondeliverables']):
            _path = os.path.join(info.path, subdir)
            os.mkdir(_path)
            # git won't commit empty directories
            open(os.path.join(_path, '.keep'), 'w').close()
        # ----------------------------------------------------------------------

        # create project metadata
        project['project-id'] = client['id']
        project['project-url'] = client['url']
        project['version'] = 1
        meta = '_'.join([
            project['project-name'],
            project['specification'],
            'meta.yml'
        ]) # implicit versioning
        meta = Metadata(project, metapath=meta, skip_keys=['environment'])
        meta.validate()
        meta.write(validate=False)
        # ----------------------------------------------------------------------

        # commit everything
        local.add(all=True)
        local.commit(
            'VALID PROJECT:\n\t{} created according to {} specification'.format(
                info.name,
                project['specification']
            )
        )
        local.push('dev')
        client.has_branch('dev', timeout=10)
        client.set_default_branch('dev')

        # add teams
        for team, perm in project['teams'].items():
            client.add_team(team, perm)
        # ----------------------------------------------------------------------

        # cleanup
        os.chdir(info.config['project-root'])
        shutil.rmtree(info.path) # problem if currently in info.path

        return True

    def clone(self, name=None, **config):
        r'''
        Clones a nerve project to local project-root directory

        Ensures given branch is present in the repository

        Args:
            name (str, optional): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            project (dict, \**config): project metadata.
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2
            user_branch (str, \**config): branch to clone from. Default: user's branch

        Returns:
            bool: success status

        .. todo::
            - catch repo already exists errors and repo doesn't exist errors
        '''
        info = self._get_info(name, None, config)

        client = Client(info.client_conf)
        if client.has_branch(info.branch):
            local = Git(info.path, url=client['url'], branch=info.branch, environment=info.env)
        else:
            local = Git(info.path, url=client['url'], branch='dev', environment=info.env)

            # this done in lieu of doing it through github beforehand
            local.branch(info.branch)
            local.push(info.branch)

        return True

    def request(self, name=None, **config):
        r'''
        Request deliverables from the dev branch of given project

        Args:
            name (str, optional): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            project (dict, \**config): project metadata.
            user_branch (str, \**config): branch to pull deliverables into. Default: user's branch
            request_include_patterns (list, \**config): list of regular expressions user to include specific deliverables
            request_exclude_patterns (list, \**config): list of regular expressions user to exclude specific deliverables
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status
        '''
        info = self._get_info(name, None, config)

        local = Git(info.path, branch=info.branch, environment=info.env)
        local.branch('dev')
        local.pull('dev')
        local.merge('dev', info.branch)
        local.branch(info.branch)

        lfs = GitLFS(info.path, environment=info.env)
        lfs.pull(
            info.config['request-include-patterns'],
            info.config['request-exclude-patterns']
        )

        return True
    # --------------------------------------------------------------------------

    def _update_local(self, info):
        '''
        Convenience method for merging remote dev branch into local user branch

        Ensures non-fastforward merge conflicts don't occur

        Args:
            info (tuple): info object returned by _get_info

        Returns:
            None
        '''
        # pulling metadata first avoids merge conflicts by keeping the
        # user-branch HEAD ahead of the dev branch
        local = Git(info.path, branch=info.branch, environment=info.env)
        local.branch('dev')
        local.pull('dev')
        local.merge('dev', info.branch)
        local.branch(info.branch)

    def _publish_nondeliverables(self, info):
        '''
        Convenience method for publishing nondeliverable assets

        Assets published to user branch

        Args:
            info (tuple): info object returned by _get_info

        Returns:
            None
        '''
        # get nondeliverable assets
        info.config['status-asset-types'] = ['nondeliverable']
        nondeliverables = self.status(name=info.name, **info.config)
        nondeliverables = list(nondeliverables)
        for non in nondeliverables:
            non.get_traits()
            non.write(validate=False)

        # publish nondeliverables
        if len(nondeliverables) > 0:
            lfs = GitLFS(info.path, environment=info.env)
            local = Git(info.path, branch=info.branch, environment=info.env)

            # push non-deliverables to user-branch
            local.add([x.metapath for x in nondeliverables])
            local.add([x.datapath for x in nondeliverables])
            names = [x['asset-name'] for x in nondeliverables]
            local.commit('NON-DELIVERABLES:\n\t' + '\n\t'.join(names))
            local.push(info.branch)

    def _get_deliverables(self, info):
        '''
        Convenience method for retrieving valid and invalid deliverable assets

        Args:
            info (tuple): info object returned by _get_info

        Returns:
            tuple: valid deliverables, invalid deliverables
        '''
        config = info.config

        # get only added deliverable assets
        if 'project' in config.keys():
            del config['project']
        deliverables = self.status(
            name=info.name,
            status_states=['added'],
            status_asset_types=['deliverable'],
            project={
                'project-id': info.project['project-id'],
                'project-url': info.project['project-url']
            },
            **config
        )

        invalid = []
        valid = []
        for deliv in deliverables:
            deliv.get_traits()
            deliv.write()
            try:
                deliv.validate()
            except ValidationError as e:
                if info.verbosity > 0:
                    warn(e)
                invalid.append(deliv)
                continue
            valid.append(deliv)

        return valid, invalid

    def publish(self, name=None, notes=None, **config):
        r'''
        Attempt to publish deliverables from user's branch to given project's dev branch on Github

        All assets will be published to the user's branch.
        If all deliverables are valid then all data and metadata will be commited
        to the user's branch and merged into the dev branch.
        If not only invalid metadata will be commited to the user's branch

        Args:
            name (str, optional): name of project. Default: None
            notes (str, optional): notes to appended to project metadata. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            project (dict, \**config): project metadata.
            user_branch (str, \**config): branch to pull deliverables from. Default: user's branch
            publish_include_patterns (list, \**config): list of regular expressions user to include specific assets
            publish_exclude_patterns (list, \**config): list of regular expressions user to exclude specific assets
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status

        .. todo::
            - add branch checking logic to skip the following if not needed?
        '''
        info = self._get_info(name, notes, config)
        self._publish_nondeliverables(info)
        self._update_local(info)
        valid, invalid = self._get_deliverables(info)
        # ----------------------------------------------------------------------

        client = Client(info.client_conf)
        local = Git(info.path, branch=info.branch, environment=info.env)
        lfs = GitLFS(info.path, environment=info.env)

        if len(invalid) > 0:
            # commit only invalid metadata to github user branch
            local.add([x.metapath for x in invalid])
            local.commit('INVALID DELIVERABLES:\n\t' + '\n\t'.join([x['asset-name'] for x in invalid]))
            local.push(info.branch)
            return False

        else:
            # commit all deliverable data and metadata to github dev branch
            local.add([x.metapath for x in valid])
            local.add([x.datapath for x in valid])
            names = [x['asset-name'] for x in valid]
            local.commit('VALID DELIVERABLES:\n\t' + '\n\t'.join(names))
            local.push(info.branch)

            title = '{user} attempts to publish valid deliverables to dev'
            title = title.format(user=info.branch)
            body = []
            body.append('publisher: **{user}**')
            body.append('deliverables:')
            body.extend(['\t' + x for x in names])
            body = '\n'.join(body)
            body = body.format(user=info.branch)

            sha = local.sha
            remote_sha = client.get_head_sha(info.branch)
            while sha != remote_sha:
                remote_sha = client.get_head_sha(info.branch)

            # this produces a race condition with the local.push process
            num = client.create_pull_request(title, 'dev', info.branch, body=body)
            client.merge_pull_request(num, 'Publish authorized')

            return True
    # --------------------------------------------------------------------------

    def delete(self, from_server, from_local, name=None, **config):
        r'''
        Deletes a nerve project

        Args:
            from_server (bool): delete Github project
            from_local (bool): delete local project directory
            name (str, optional): name of project. Default: None
            \**config: optional config parameters, overwrites fields in a copy of self.config
            project (dict, \**config): project metadata.
            verbosity (int, \**config): level of verbosity for output. Default: 0
                Options: 0, 1, 2

        Returns:
            bool: success status

        .. todo::
            - add git lfs logic for deletion
        '''
        info = self._get_info(name, None, config)

        if from_server:
            Client(info.client_conf).delete()
            # git lfs deletion logic
        if from_local:
            if os.path.split(info.path)[-1] == info.name:
                if os.path.exists(info.path):
                    shutil.rmtree(info.path)
            else:
                warn(info.path + ' is not a project directory.  Local deletion aborted.')
                return False
        return True
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
