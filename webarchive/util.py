"""Utility classes and functions for internal use."""

import re

from base64 import b64encode
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin


__all__ = ["base64_string", "bytes_to_str",
           "process_main_resource", "process_style_sheet"]


# Regular expression matching a URL in a style sheet
RX_STYLE_SHEET_URL = re.compile(r"url\(([^\)]+)\)")


class MainResourceProcessor(HTMLParser):
    """Class to process the main resource in the webarchive.

    This class uses HTMLParser to rewrite the main resource's HTML code
    to make changes necessary to render the extracted page:

      * All href and src attributes referring to subresources in the
        archive are changed to point to the local extracted copies.

      * The optional srcset attribute is removed from <img> tags, since
        it causes rendering problems when extracting webarchives saved by
        older versions of Safari that don't support that attribute.
    """

    __slots__ = ["_url", "_root", "_subresources", "_local_paths", "_output"]

    def __init__(self, url, root, subresources, local_paths, output):
        """Return a new MainResourceProcessor."""

        HTMLParser.__init__(self, convert_charrefs=False)

        self._url = url
        self._root = root
        self._subresources = subresources
        self._local_paths = local_paths
        self._output = output

    def handle_starttag(self, tag, attrs):
        """Handle the start of a tag."""

        if self._root is None:
            inline_content = None

            if tag == "link":
                link_href = None
                is_stylesheet = False
                for attr, value in attrs:
                    if attr == "rel" and value.lower() == "stylesheet":
                        is_stylesheet = True
                    elif attr == "href":
                        link_href = self._absolute_url(value)
                if is_stylesheet:
                    # Replace this link with an inline <style> block
                    content = ""
                    for subresource in self._subresources:
                        if subresource.url == link_href:
                            data = process_style_sheet(subresource,
                                                       self._subresources)
                            content = escape(data)
                            break
                    # Bypass the standard logic since we're replacing this
                    # with an entirely different tag
                    self._output.write("<style>{0}</style>".format(content))
                    return

            elif tag == "script":
                for i, (attr, value) in enumerate(attrs):
                    if attr == "src":
                        # Include the script content inline
                        script_src = self._absolute_url(value)
                        for subresource in self._subresources:
                            if subresource.url == script_src:
                                # HTML entities in <script> are NOT escaped
                                inline_content = bytes_to_str(subresource.data)
                                break
                        # Remove the src attribute
                        del attrs[i]

        # Open the tag
        tag_data = ["<", tag]

        # Process attributes
        for attr, value in attrs:
            if tag == "img" and attr == "srcset":
                # Omit the srcset attribute, which is not supported by older
                # versions of Safari (including the obsolete 5.1.7 for Windows,
                # which is the only version I have available to test with).
                continue

            tag_data.append(" ")
            tag_data.append(attr)
            tag_data.append('="')
            tag_data.append(self._process_attr_value(tag, attr, value))
            tag_data.append('"')

        # Close the tag
        tag_data.append(">")

        # If this is the opening <html> tag, indicate that this file
        # has been processed
        if tag == "html":
            tag_data.insert(0, "<!-- Processed by pywebarchive -->\n")

        self._output.write("".join(tag_data))
        if self._root is None and inline_content:
            self._output.write(inline_content)

    def handle_endtag(self, tag):
        """Handle the end of a tag."""

        self._output.write("</{0}>".format(tag))

    def handle_data(self, data):
        """Handle arbitrary data."""

        self._output.write(escape(data, False))

    def handle_entityref(self, name):
        """Handle a named character reference."""

        self._output.write("&{0};".format(name))

    def handle_charref(self, name):
        """Handle a numeric character reference."""

        self._output.write("&#{0};".format(name))

    def handle_comment(self, data):
        """Handle a comment."""

        # Note IE conditional comments potentially can affect rendering
        self._output.write("<!--{0}-->".format(data))

    def handle_decl(self, decl):
        """Handle a doctype declaration."""

        # This should probably be on its own line
        self._output.write("<!{0}>\n".format(decl))

    def _absolute_url(self, url):
        """Return the absolute URL to the specified resource."""

        return urljoin(self._url, url)

    def _resource_url(self, orig_url):
        """Return an appropriate URL for the specified resource.

        If the resource exists in this archive, this will be its local path.
        Otherwise, it will be the absolute URL to the original resource.
        """

        # Get the absolute URL of the original resource
        abs_url = self._absolute_url(orig_url)

        if abs_url in self._local_paths:
            # Return the local path to this resource
            if self._root:
                return "{0}/{1}".format(self._root,
                                        self._local_paths[abs_url])
            else:
                return self._local_paths[abs_url]

        else:
            # Return the absolute URL to this resource
            return abs_url

    def _process_attr_value(self, tag, attr, value):
        """Process the value of a tag's attribute."""

        if tag == "a" and attr == "href":
            value = self._absolute_url(value)

        elif tag == "img":
            if attr == "src":
                if self._root:
                    value = self._resource_url(value)
                else:
                    # Inline this image using a data URI
                    for subresource in self._subresources:
                        if subresource.url == self._absolute_url(value):
                            value = subresource.to_data_uri()

            elif attr == "srcset":
                # Process the HTML5 srcset attribute
                srcset = []
                for item in map(str.strip, value.split(",")):
                    src, res = item.split(" ", 1)
                    src = self._resource_url(src)
                    srcset.append("{0} {1}".format(src, res))

                value = ", ".join(srcset)

        elif attr in ("action", "href", "src"):
            value = self._resource_url(value)

        return escape(value, True)


def base64_string(data, altchars=None):
    """Return data encoded as a base64 string."""
    return bytes_to_str(b64encode(data, altchars))


def bytes_to_str(data):
    """Convert bytes to str."""
    return "".join(map(chr, data))


def process_main_resource(res,
                          subresource_dir, subresources, local_paths, output):
    """Process a webarchive's main WebResource."""

    # Feed the content through the MainResourceProcessor to rewrite
    # references to files inside the archive
    mrp = MainResourceProcessor(res.url, subresource_dir,
                                subresources, local_paths, output)
    mrp.feed(str(res))


def process_style_sheet(res, subresources, local_paths=None):
    """Process a WebResource containing CSS data.

    If local_paths is specified, any url() value referencing another
    subresource in this webarchive will be replaced with the local path
    of the extracted copy. If no local_paths are specified, references
    to other subresources in this webarchive will be replaced with data
    URIs corresponding to their contents.
    """

    content = str(res)

    # Find URLs in the stylesheet
    matches = RX_STYLE_SHEET_URL.findall(content)
    for match in matches:
        # Remove quote characters, if present, from the URL
        if match.startswith('"') or match.startswith("'"):
            match = match[1:]
        if match.endswith('"') or match.endswith("'"):
            match = match[:-1]

        # Filter out blank URLs; we really shouldn't encounter these
        # in the first place, but they can show up and cause problems
        if not match:
            continue

        # Get the absolute URL of the original resource.
        # Note paths in CSS are relative to the style sheet.
        abs_url = urljoin(res.url, match)

        if local_paths:
            if abs_url in local_paths:
                # Substitute the local path to this resource.
                # Because paths in CSS are relative to the style sheet,
                # and all subresources (like style sheets) are extracted
                # to the same folder, the basename is all we need.
                local_url = local_paths[abs_url]
                content = content.replace(match, local_url)

            else:
                # Substitute the absolute URL of this resource.
                content = content.replace(match, abs_url)

        else:
            # Substitute the absolute URL if this resource,
            # unless we find it in this webarchive.
            replacement = abs_url
            for subresource in subresources:
                if subresource.url == abs_url:
                    # This subresource is in our webarchive,
                    # so inline its contents using a data URI.
                    replacement = subresource.to_data_uri()
                    break

            content = content.replace(match, abs_url)

    return content
