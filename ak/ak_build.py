# coding: utf-8
"""AK."""
import logging

from plumbum import cli, local
from plumbum.cmd import (
    mkdir, ls, find, ln,
    gunzip, git, wget, python)
from plumbum.commands.modifiers import FG, TF, BG, RETCODE
from datetime import datetime
import os
import ConfigParser
import yaml

from .ak_sub import AkSub, Ak

MODULE_FOLDER = 'modules'


REPO_YAML = 'repo.yaml'
SPEC_YAML = 'spec.yaml'
VENDOR_FOLDER = 'external-src'


@Ak.subcommand("init")
class AkInit(AkSub):
    "Build dependencies for odoo"

    def main(self, *args):
       print "init project"
       print """
       propose de selectionner une majeur ?
       export WORKON_HOME=`pwd`
       if requirements or pipfile exit
       echo 'workspace-*' >> .gitignore
       wget https://raw.githubusercontent.com/odoo/odoo/10.0/requirements.txt
       pipenv install
       pipenv install http://nightly.odoo.com/10.0/nightly/src/odoo_10.0.latest.zip
       git add requirements.txt
       git add Pipfile
       #add odoo addons dans le Pipfile

       export ODOO_RC='/workspace/odoo_base.cfg' # project wide

       """



@Ak.subcommand("build")
class AkBuild(AkSub):
    "Build dependencies for odoo"

    fileonly = cli.Flag(
        '--fileonly', help="Just generate the %s" % REPO_YAML, group="IO")
    output = cli.SwitchAttr(
        ["o", "output"], default=REPO_YAML, help="Output file", group="IO")
    config = cli.SwitchAttr(
        ["c", "config"], default=SPEC_YAML, help="Config file", group="IO")

    def _convert_repo(self, repo):
        if repo.get('remotes'):
            repo.pop('modules', None)
            if not repo.get('target'):
                repo['target'] = '%s fake' % repo['remotes'].keys()[0]
            return repo
        else:
            src = repo['src'].split(' ')
            # case we have specify the url and the branch
            if len(src) == 2:
                src, branch = src
                commit = None
            # case we have specify the url and the branch and the commit
            elif len(src) == 3:
                src, branch, commit = src
            else:
                raise Exception(
                    'Src must be in the format '
                    'http://github.com/oca/server-tools 10.0 <optional sha>')
            return {
                'remotes': {'src': src},
                'merges': ['src %s' % (commit or branch)],
                'target': 'src fake'
                }

    def _generate_repo_yaml(self):
        repo_conf = {}
        config = yaml.load(open(self.config).read())
        for key in config:
            repo_conf[key] = self._convert_repo(config[key])
        data = yaml.dump(repo_conf)
        with open(self.output, 'w') as output:
            output.write(data)

    def main(self, *args):
        self._generate_repo_yaml()
        if not self.fileonly:
            with local.cwd(VENDOR_FOLDER):
                local['gitaggregate']['-c', '../' + self.output] & FG


@Ak.subcommand("freeze")
class AkFreeze(AkSub):
    "Freeze dependencies for odoo"

    def main(self):
        self._exec(
            'pipenv',
            ['lock'])


@Ak.subcommand("link")
class AkLink(AkSub):
    "Link modules defined in repos.yml/yaml in modules folder"

    config_spec = cli.SwitchAttr(
        ["c", "config"], default=SPEC_YAML, help="Config file", group="IO")

    def main(self, file=None, config=None):
        config = yaml.load(open(self.config_spec).read())
        dest_path = local.path(MODULE_FOLDER)

        self._clear_dir(dest_path)
        for repo_path, repo in config.items():
            modules = repo.pop('modules', [])
            self._set_links(repo_path, modules, dest_path)

    def _clear_dir(self, path):
        "Create dir or remove links"
        if not path.exists():
            mkdir(path)
        with local.cwd(path):
            find['.']['-type', 'l']['-delete']()

    def _set_links(self, repo_path, modules, dest_path):
        for module in modules:
            src = '../%s/%s' % (repo_path, module)
            ln['-s', src, dest_path]()
