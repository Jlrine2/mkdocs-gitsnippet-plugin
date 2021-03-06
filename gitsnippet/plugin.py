from mkdocs.plugins import BasePlugin

from jinja2 import Template
from git import Repo
from urllib.parse import urlparse
import uuid
import shutil
import re
import os
import mkdocs
import requests
import sys


def is_url(path):
    parsed_url = urlparse(path)
    return all([parsed_url.scheme, parsed_url.netloc, parsed_url.path])


class GitSnippetPlugin(BasePlugin):

    if sys.version_info[0] == 3:
        string_types = str
    else:
        string_types = basestring

    config_scheme = (('base_path',
                      mkdocs.config.config_options.Type(
                          string_types, default='docs')), )

    page = None

    def copy_markdown_images(self, tmpRoot, markdown):
        # root = os.path.dirname(os.path.dirname(self.page.url))
        root = self.page.url

        paths = []

        p = re.compile("!\[.*?\]\((.*?)\)")
        it = p.finditer(markdown)
        for match in it:
            path = match.group(1)

            destinationPath = os.path.realpath(self.config['base_path'] + "/" +
                                               root + "/gen_/" + path)
            filepath = tmpRoot + '/' + destinationPath
            paths.append(destinationPath)
            if not os.path.isfile(filepath):
                print("Copying image: " + path + " to " + destinationPath)

                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                if is_url(path):
                    response = requests.get(path)
                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content():
                            if chunk:
                                f.write(chunk)
                else:
                    shutil.copyfile(filepath, destinationPath)

        for path in paths:
            markdown = markdown.replace(path, "gen_/" + path)

        return markdown

    def markdown_gitsnippet(self, git_url, file_path, section_name, branch=None):
        p = re.compile("^#+ ")
        m = p.search(section_name)
        id = uuid.uuid4().hex
        root = "/tmp/" + id
        r = Repo.clone_from(git_url, root)

        if branch is not None:
            r.git.checkout(branch)

        content = ""
        with open(root + '/' + file_path, 'r') as myfile:
            content = myfile.read()

        if section_name != "" and m:
            section_level = m.span()[1] - 1
            p = re.compile("^" + section_name + "$", re.MULTILINE)
            start = p.search(content)
            start_index = start.span()[1]

            p = re.compile("^#{1," + str(section_level) + "} ", re.MULTILINE)

            end = p.search(content[start_index:])
            if end:
                end_index = end.span()[0]
                content = content[start_index:end_index + start_index]
            else:
                content = content[start_index:]
        
        # If there are any images, find them, copy them
        content = self.copy_markdown_images(root, content)

        # Delete all root files
        shutil.rmtree(root)
        return content

    def gitsnippet(self, git_url, file_path, section_name, branch):
        if file_path.endswith('.md'):
            return self.markdown_gitsnippet(git_url, file_path, section_name, branch)
        else:
            return "File format not supported"

    def on_page_markdown(self, markdown, page, config, **kwargs):
        self.page = page
        md_template = Template(markdown)
        return md_template.render(gitsnippet=self.gitsnippet)
